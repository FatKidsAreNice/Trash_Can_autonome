import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_FILE = os.path.join(BASE_DIR, "detected_objects.json")

# Stelle sicher, dass hier ein LEICHTES Modell genutzt wird (z.B. yolov8n.pt)
# Wenn du yolov8m.pt oder 'x' nutzt, ruckelt es zu stark.
# Wir nutzen BASE_DIR, das oben in der Datei schon definiert ist
MODEL_PATH = os.path.join(BASE_DIR, "yolo11s.engine")

# Kamera
CAM_WIDTH = 1920
CAM_HEIGHT = 1080
CAM_FPS = 60 # 60 ist für YOLO oft unnötig und belastet den Buffer

# Logik
MEMORY_TOLERANCE = 10 # Reduziert, damit verlorene Objekte schneller in History gehen
BORDER_MARGIN = 10
SCALE_FACTOR = 0.8 

# Tracking TUNING
# Bei 1080p und niedrigen FPS muss dieser Wert HOCH sein.
# Wenn ein Objekt in 0.2 Sekunden (5 FPS) 300 Pixel wandert, muss der Wert > 300 sein.
MAX_TRACKING_DISTANCE = 400 
RECOVERY_DISTANCE = 500     
HISTORY_DURATION = 5.0 # Wie lange wir uns an ein verlorenes Objekt erinnern

# YOLO
CONFIDENCE_THRESHOLD = 0.7 # Etwas toleranter sein
