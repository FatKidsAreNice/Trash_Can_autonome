# Datei: yolo_detector.py
from ultralytics import YOLO
import cv2
import numpy as np
import config

class YoloDetector:
    def __init__(self):
        print(f"Lade YOLO Modell: {config.MODEL_PATH}...")
        # task='detect' hilft manchmal bei Engine-Dateien, Fehler zu vermeiden
        self.model = YOLO(config.MODEL_PATH, task='detect')
        print("Modell geladen.")

    def detect(self, frame):
        img_h, img_w = frame.shape[:2]
        
        # Inferenz mit dem Engine-Modell
        results = self.model(frame, verbose=False, conf=config.CONFIDENCE_THRESHOLD)
        detected_objects = []
        
        if not results: return []
        
        result = results[0]
        
        for box in result.boxes:
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
            
            x = int(x1)
            y = int(y1)
            w = int(x2 - x1)
            h = int(y2 - y1)
            
            conf = float(box.conf[0])
            cls_id = int(box.cls[0])
            
            # Label holen
            if hasattr(result, 'names'):
                label = result.names[cls_id]
            else:
                label = "unknown"

            # --- FILTER START ---
            
            # WICHTIG: Liste der Dinge, die der Roboter jagen soll.
            # 'sports ball' ist der Trick für Papierkugeln!
            TARGET_CLASSES = ["bottle", "cup", "can", "sports ball", "orange", "apple"]

            if label.lower() not in TARGET_CLASSES:
                # Debugging: Entferne das # unten, um zu sehen, was er sonst so erkennt
                # print(f"Ignoriere: {label}") 
                continue

            # Größen-Filter
            if w < 20 or h < 20:
                continue

            # Rand-Filter
            margin = 5
            if x < margin or y < margin or (x + w) > (img_w - margin) or (y + h) > (img_h - margin):
                continue
            
            # --- FILTER ENDE ---
            
            detected_objects.append({
                "label": label,
                "box": (x, y, w, h),
                "conf": conf
            })
            
        return detected_objects
