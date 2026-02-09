# config.py
"""
Globale Konfiguration und Konstanten.

Zweck
-----
Zentralisiert alle Parameter ("Magic Numbers"), um Tuning zu erleichtern,
ohne die Logik-Dateien ändern zu müssen.
"""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_FILE = os.path.join(BASE_DIR, "detected_objects.json")

# --- KI Modell ---
# Nutzung von TensorRT (.engine) statt PyTorch (.pt) für 
# massive Performance-Gewinne auf Nvidia Jetson Hardware.
MODEL_PATH = os.path.join(BASE_DIR, "yolo11s.engine")

# --- Kamera-Einstellungen ---
CAM_WIDTH = 1920
CAM_HEIGHT = 1080
CAM_FPS = 60 # Hohe Framerate, Buffer-Management geschieht in JetsonCamera.py

# --- Pre-Processing & Logik ---
MEMORY_TOLERANCE = 10 # Hysterese: Wie viele Frames darf ein Objekt fehlen, bevor ID gelöscht wird?
BORDER_MARGIN = 10
SCALE_FACTOR = 0.8    # Inferenz auf kleinerem Bild spart Rechenzeit

# --- Tracking Algorithmus Tuning ---
# Diese Werte definieren, wann ein Objekt als "dasselbe" wie im vorherigen Frame gilt.
MAX_TRACKING_DISTANCE = 400 # Pixel-Radius für Frame-zu-Frame Matching
RECOVERY_DISTANCE = 500     # Suchradius für Wiederfinden nach Verdeckung
HISTORY_DURATION = 5.0      # Zeit in Sekunden für das "Gedächtnis" des Trackers

# --- Inferenz Parameter ---
CONFIDENCE_THRESHOLD = 0.7 # Nur sichere Erkennungen zulassen
