import time
import signal
import cv2
import argparse
import serial 

# Eigene Module
import config
from tracker_logic import ObjectManager
from gui import draw_overlay
from yolo_detector import YoloDetector
from robot_brain import RobotBrain 

# Hardware
from JetsonCamera import Camera
from Focuser import Focuser
from Autofocus import FocusState, doFocus

exit_ = False

def sigint_handler(signum, frame):
    global exit_
    exit_ = True

signal.signal(signal.SIGINT, sigint_handler)
signal.signal(signal.SIGTERM, sigint_handler)

def parse_cmdline():
    parser = argparse.ArgumentParser(description='Arducam YOLO Object Tracker')
    parser.add_argument('-i', '--i2c-bus', type=int, required=True, help='I2C Bus (meist 6, 7 oder 8)')
    parser.add_argument('-v', '--verbose', action="store_true")
    return parser.parse_args()

def main():
    print("\n--- STARTE KI-OBJEKT TRACKER ---\n")
    args = parse_cmdline()
    
    # 1. Hardware Init
    camera = Camera(width=config.CAM_WIDTH, height=config.CAM_HEIGHT)
    focuser = Focuser(args.i2c_bus)
    try: focuser.set(2000)
    except: pass
    focusState = FocusState()
    
    print("Warte auf Kamera...")
    time.sleep(2)

    print("Verbinde mit Arduino...")
    try:
        arduino = serial.Serial('/dev/ttyACM0', 9600, timeout=0.1)
        time.sleep(2) 
        print("Arduino verbunden!")
    except Exception as e:
        print(f"ACHTUNG: Kein Arduino gefunden! ({e})")
        arduino = None
    
    # 2. KI Init
    detector = YoloDetector() 
    tracker = ObjectManager(config.JSON_FILE)
    brain = RobotBrain(wait_time=2.0, search_duration=10.0)

    cv2.namedWindow("Tracking", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Tracking", 1280, 720)

    # Initiale Fokus-Setzung
    focuser.set(Focuser.OPT_FOCUS, 2000) 
    current_focus = 2000
    
    # --- TIMER FÜR AUTO-FOKUS ---
    last_focus_time = time.time()
    # ----------------------------

    while not exit_:
        frame = camera.getFrame(2000)
        if frame is None: continue

        # --- HIER WURDE cv2.rotate ENTFERNT ---
        # Das macht jetzt die JetsonCamera.py per Hardware!
        
        height, width = frame.shape[:2]
        
        # KI Detection
        small_frame = cv2.resize(frame, (0, 0), fx=config.SCALE_FACTOR, fy=config.SCALE_FACTOR)
        detections = detector.detect(small_frame)
        
        # Hochskalieren
        inv_scale = 1.0 / config.SCALE_FACTOR
        scaled_detections = []
        for det in detections:
            x, y, w, h = det['box']
            scaled_detections.append({
                'label': det['label'],
                'box': (int(x*inv_scale), int(y*inv_scale), int(w*inv_scale), int(h*inv_scale))
            })

        # Tracker & Brain
        active_entities = tracker.process(scaled_detections, width, height)
        
        target_entity = None
        max_area = 0
        for uid, entity in active_entities.items():
            if entity.active:
                area = entity.box[2] * entity.box[3]
                if area > max_area:
                    max_area = area
                    target_entity = entity

        throttle, steering, status_text, color = brain.calculate_move(target_entity, width)

        # Arduino
        if arduino:
            try:
                cmd = f"<{throttle:.2f},{steering:.2f}>\n"
                arduino.write(cmd.encode())
            except Exception as e: pass

        # --- AUTO-FOKUS LOGIK ---
        if time.time() - last_focus_time > 1.0: # Jede Sekunde
            if focusState.isFinish(): # Nur wenn er nicht eh schon beschäftigt ist
                focusState.reset()
                doFocus(camera, focuser, focusState)
                last_focus_time = time.time()
        # ------------------------

        # GUI
        draw_overlay(frame, width, height, active_entities)
        cv2.putText(frame, f"Mode: {status_text}", (30, 150), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
        cv2.putText(frame, f"CMD: T={throttle:.2f} S={steering:.2f}", (30, 190), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

        cv2.imshow("Tracking", frame)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'): break
        elif key == ord('f'): # Manueller Trigger bleibt erhalten
            focusState.reset()
            doFocus(camera, focuser, focusState)

    if arduino: arduino.close()
    camera.close()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
