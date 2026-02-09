# robot_brain.py
"""
Steuerungslogik / Regelungstechnik.

Zweck
-----
Übersetzt die Position des getrackten Objekts (Vision-Daten) in 
physikalische Steuerbefehle (Gas/Lenkung) für die Motorsteuerung.

Algorithmus:
- Lenkung: Proportional-Regler (P-Controller). Versucht, den Fehler 
  (Abstand Objektmitte zu Bildmitte) zu minimieren.
- Gas: Einfache Zustandslogik (Bang-Bang Controller mit Hysterese-Ansatz). 
  Stoppt, wenn das Objekt groß genug erscheint (nah genug).
"""

import time

class RobotBrain:
    def __init__(self, wait_time=2.0, search_duration=10.0):
        # Konfiguration für Zustandsübergänge
        self.WAIT_TIME = wait_time
        self.SEARCH_DURATION = search_duration
        
        # State-Variablen
        self.has_seen_object_once = False
        self.last_detection_time = time.time()
        
        # Tuning-Parameter (Regler-Gains)
        self.STEERING_GAIN = 0.6       # Wie stark lenkt er bei Abweichung?
        self.TARGET_WIDTH_RATIO = 0.4  # Zielgröße: Wenn Objekt 40% der Bildbreite einnimmt -> Stopp
        self.SPEED_APPROACH = 0.65     # Geschwindigkeit beim Verfolgen
        self.SPEED_SEARCH = 0.4        # Geschwindigkeit (theoretisch) beim Suchen

    def calculate_move(self, target_entity, frame_width):
        """
        Haupt-Berechnungsfunktion.
        
        Input: 
            target_entity: Das aktuell priorisierte Objekt (oder None).
            frame_width: Bildbreite zur Berechnung der Mitte.
            
        Output: 
            (throttle, steering, status_text, status_color)
        """
        throttle = 0.0
        steering = 0.0
        status_text = "IDLE"
        color = (0, 0, 255) # Rot (Standard: Stop)

        if target_entity:
            # --- ZUSTAND: TRACKING (Objekt sichtbar) ---
            
            # 1. Lenk-Regelung (Lateral Control)
            # Ziel ist es, error_x auf 0 zu bringen.
            center_x = frame_width / 2
            obj_x = target_entity.box[0] + (target_entity.box[2] / 2)
            
            # Normalisierter Fehler (-1.0 = ganz links, +1.0 = ganz rechts)
            error_x = (obj_x - center_x) / (frame_width / 2)
            steering = error_x * self.STEERING_GAIN

            # 2. Geschwindigkeits-Regelung (Longitudinal Control)
            # Wir nutzen die Breite der Bounding Box als Proxy für die Entfernung.
            current_width_ratio = target_entity.box[2] / frame_width
            
            if current_width_ratio < self.TARGET_WIDTH_RATIO:
                # Objekt ist klein -> wir sind weit weg -> Fahren
                throttle = self.SPEED_APPROACH
            else:
                # Objekt ist groß -> wir sind am Ziel -> Bremsen
                throttle = 0.0 
            
            status_text = "TRACKING"
            color = (0, 255, 0) # Grün

        else:
            # --- ZUSTAND: VERLOREN / STOP ---
            # Failsafe-Modus: Wenn kein Ziel da ist, bleiben wir sofort stehen.
            throttle = 0.0
            steering = 0.0
            status_text = "NO TARGET - STOPPED"
            color = (0, 0, 255)

        return throttle, steering, status_text, color
