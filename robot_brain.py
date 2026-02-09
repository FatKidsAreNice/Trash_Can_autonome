import time

class RobotBrain:
    def __init__(self, wait_time=2.0, search_duration=10.0):
        # Konfiguration
        self.WAIT_TIME = wait_time
        self.SEARCH_DURATION = search_duration
        
        # State
        self.has_seen_object_once = False
        self.last_detection_time = time.time()
        
        # PID / Regelung Tuning
        self.STEERING_GAIN = 0.6
        self.TARGET_WIDTH_RATIO = 0.4
        self.SPEED_APPROACH = 0.65
        self.SPEED_SEARCH = 0.4

    def calculate_move(self, target_entity, frame_width):
        """
        Entscheidet basierend auf dem Ziel, was zu tun ist.
        Gibt zurück: (throttle, steering, status_text, status_color)
        """
        throttle = 0.0
        steering = 0.0
        status_text = "IDLE"
        color = (0, 0, 255) # Rot

        if target_entity:
            # --- MODUS: VERFOLGEN ---
            
            # 1. Lenkung berechnen (Mitte finden)
            center_x = frame_width / 2
            obj_x = target_entity.box[0] + (target_entity.box[2] / 2)
            error_x = (obj_x - center_x) / (frame_width / 2)
            steering = error_x * self.STEERING_GAIN

            # 2. Gas berechnen (Abstand prüfen)
            current_width_ratio = target_entity.box[2] / frame_width
            if current_width_ratio < self.TARGET_WIDTH_RATIO:
                throttle = self.SPEED_APPROACH
            else:
                throttle = 0.0 # Stopp, wir sind nah genug
            
            status_text = "TRACKING"
            color = (0, 255, 0) # Grün

        else:
            # --- MODUS: STOPP (Objekt verloren oder nie gesehen) ---
            # Hier passiert jetzt nichts mehr. Der Roboter bleibt einfach stehen.
            throttle = 0.0
            steering = 0.0
            status_text = "NO TARGET - STOPPED"
            color = (0, 0, 255)

        return throttle, steering, status_text, color
