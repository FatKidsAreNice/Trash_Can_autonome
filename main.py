# main.py
"""
Hauptsteuerung / Entry-Point für den KI-Tracker.

Zweck
-----
Diese Datei orchestriert die gesamte Roboter-Software:
1. Hardware-Initialisierung: Startet Kamera, Fokus-Motor und serielle Verbindung (Arduino).
2. KI-Pipeline: Lädt das YOLO-Modell und den Objekt-Tracker.
3. Echtzeit-Schleife (Soft Real-Time):
    - Bildaufnahme (Frame grabbing)
    - Inferenz (Objekterkennung)
    - Logik-Verarbeitung (Tracking & Bewegungsberechnung)
    - Aktorik (Senden der Steuerbefehle an den Arduino)
    - Visualisierung (Overlay für Debugging)

Design-Notizen
--------------
- Ereignisgesteuertes Beenden: Nutzt `signal`, um SIGINT (Strg+C) sauber abzufangen.
- Hardware-Abstraktion: Kamera und Motoren sind in Klassen gekapselt, um den Code lesbar zu halten.
- Fehlertoleranz: Der Arduino-Verbindungsaufbau ist in try/except-Blöcken geschützt, damit das System
  auch ohne Antrieb zu Debug-Zwecken (nur Kamera) laufen kann.
"""

import time
import signal
import cv2
import argparse
import serial 

# Eigene Module (Architektur-Schichten)
import config
from tracker_logic import ObjectManager
from gui import draw_overlay
from yolo_detector import YoloDetector
from robot_brain import RobotBrain 

# Hardware-Treiber
from JetsonCamera import Camera
from Focuser import Focuser
from Autofocus import FocusState, doFocus

exit_ = False

def sigint_handler(signum, frame):
    """Fängt Systemsignale ab, um Hardware (Kamera/Serial) sauber zu schließen."""
    global exit_
    exit_ = True

signal.signal(signal.SIGINT, sigint_handler)
signal.signal(signal.SIGTERM, sigint_handler)

def parse_cmdline():
    """Verarbeitet Kommandozeilenargumente (z.B. I2C-Bus ID für den Fokus)."""
    parser = argparse.ArgumentParser(description='Arducam YOLO Object Tracker')
    parser.add_argument('-i', '--i2c-bus', type=int, required=True, help='I2C Bus (meist 6, 7 oder 8)')
    parser.add_argument('-v', '--verbose', action="store_true")
    return parser.parse_args()

def main():
    """
    Initialisierung und Hauptschleife.
    
    Ablauf:
    1. Setup von Kamera, I2C-Fokus und Serieller Schnittstelle.
    2. Laden des Neuralen Netzes (YOLO) und der Regelungs-Logik (Brain).
    3. Endlosschleife:
       - Frame holen -> KI-Detektion -> Tracking-Update -> Motor-Befehl berechnen -> Senden.
    """
    print("\n--- STARTE KI-OBJEKT TRACKER ---\n")
    args = parse_cmdline()
    
    # ---------- 1. Hardware-Schicht Initialisierung ----------
    # Kamera-Instanz erstellen (Buffer-Handling passiert intern)
    camera = Camera(width=config.CAM_WIDTH, height=config.CAM_HEIGHT)
    
    # Fokus-Motor initialisieren (Arducam I2C Steuerung)
    focuser = Focuser(args.i2c_bus)
    try: focuser.set(2000) # Standard-Fokuswert setzen
    except: pass
    focusState = FocusState()
    
    print("Warte auf Kamera...")
    time.sleep(2) # Kamerasensor benötigt Zeit zum Einpegeln (Weißabgleich/Belichtung)

    # Mikrocontroller-Kommunikation (Arduino Uno/Nano via USB)
    print("Verbinde mit Arduino...")
    try:
        # Timeout ist wichtig, damit read() nicht blockiert
        arduino = serial.Serial('/dev/ttyACM0', 9600, timeout=0.1)
        time.sleep(2) # Warten auf Arduino-Auto-Reset nach Serial-Open
        print("Arduino verbunden!")
    except Exception as e:
        print(f"ACHTUNG: Kein Arduino gefunden! ({e})")
        arduino = None
    
    # ---------- 2. Kognitive Schicht (KI & Logik) ----------
    detector = YoloDetector()                    # Kapselt das YOLOv8/11 Modell
    tracker = ObjectManager(config.JSON_FILE)    # Verwaltet Objekt-Identitäten über Frames hinweg
    brain = RobotBrain(wait_time=2.0, search_duration=10.0) # Entscheidungslogik (Regelkreis)

    # Fenster für Debug-Visualisierung
    cv2.namedWindow("Tracking", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Tracking", 1280, 720)

    # Initialer Fokus
    focuser.set(Focuser.OPT_FOCUS, 2000) 
    
    # Timer-Variablen für asynchrone Aufgaben
    last_focus_time = time.time()

    # ========== Hauptschleife (Main Loop) ==========
    while not exit_:
        # 1. Bildakquise
        frame = camera.getFrame(2000)
        if frame is None: continue

        height, width = frame.shape[:2]
        
        # 2. Perzeption (Wahrnehmung)
        # Downscaling erhöht die Inferenz-Geschwindigkeit drastisch
        small_frame = cv2.resize(frame, (0, 0), fx=config.SCALE_FACTOR, fy=config.SCALE_FACTOR)
        detections = detector.detect(small_frame)
        
        # Koordinaten-Transformation: Bounding-Boxen zurück auf Originalgröße skalieren
        inv_scale = 1.0 / config.SCALE_FACTOR
        scaled_detections = []
        for det in detections:
            x, y, w, h = det['box']
            scaled_detections.append({
                'label': det['label'],
                'box': (int(x*inv_scale), int(y*inv_scale), int(w*inv_scale), int(h*inv_scale))
            })

        # 3. Objekt-Tracking (Zuordnung von IDs zu Boxen)
        active_entities = tracker.process(scaled_detections, width, height)
        
        # 4. Zielauswahl (Heuristik: Größtes Objekt = Nächstes Objekt)
        target_entity = None
        max_area = 0
        for uid, entity in active_entities.items():
            if entity.active:
                area = entity.box[2] * entity.box[3]
                if area > max_area:
                    max_area = area
                    target_entity = entity

        # 5. Handlungsplanung (RobotBrain)
        # Berechnet Lenkwinkel und Gas basierend auf Position im Bild
        throttle, steering, status_text, color = brain.calculate_move(target_entity, width)

        # 6. Aktorik (Ausführung)
        if arduino:
            try:
                # Protokoll: <GAS, LENKUNG> als String
                cmd = f"<{throttle:.2f},{steering:.2f}>\n"
                arduino.write(cmd.encode())
            except Exception as e: pass

        # 7. Wartungsprozesse (Autofokus)
        # Wird nur periodisch (1Hz) getriggert, um den Main-Loop nicht zu bremsen
        if time.time() - last_focus_time > 1.0: 
            if focusState.isFinish(): 
                focusState.reset()
                doFocus(camera, focuser, focusState)
                last_focus_time = time.time()

        # 8. Visualisierung (GUI Update)
        draw_overlay(frame, width, height, active_entities)
        cv2.putText(frame, f"Mode: {status_text}", (30, 150), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
        cv2.putText(frame, f"CMD: T={throttle:.2f} S={steering:.2f}", (30, 190), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

        cv2.imshow("Tracking", frame)
        
        # User Input Handling
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'): break
        elif key == ord('f'): # Manueller Fokus-Trigger
            focusState.reset()
            doFocus(camera, focuser, focusState)

    # Aufräumen (Resource Cleanup)
    if arduino: arduino.close()
    camera.close()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
