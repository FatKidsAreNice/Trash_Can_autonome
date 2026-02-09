# yolo_detector.py
"""
Wrapper für die Objekterkennung (Computer Vision).

Zweck
-----
Abstrahiert die Inferenz-Bibliothek (Ultralytics YOLO). 
Nimmt ein Rohbild entgegen und liefert strukturierte Objektdaten zurück.

Funktionalität:
1. Lädt das Modell (bevorzugt TensorRT Engine Files für Jetson-Performance).
2. Führt die Inferenz durch.
3. Post-Processing:
   - Filtert irrelevante Klassen (nur Zielobjekte).
   - Filtert Artefakte am Bildrand oder zu kleine Objekte (Rauschen).
"""

from ultralytics import YOLO
import cv2
import numpy as np
import config

class YoloDetector:
    def __init__(self):
        """Initialisiert das Modell beim Start, um Latenz im Loop zu vermeiden."""
        print(f"Lade YOLO Modell: {config.MODEL_PATH}...")
        # 'task=detect' optimiert die Initialisierung für TensorRT Engines
        self.model = YOLO(config.MODEL_PATH, task='detect')
        print("Modell geladen.")

    def detect(self, frame):
        """
        Führt die Objekterkennung auf einem einzelnen Frame durch.
        
        Returns:
            Liste von Dictionaries: [{'label': str, 'box': (x,y,w,h), 'conf': float}, ...]
        """
        img_h, img_w = frame.shape[:2]
        
        # Inferenz-Schritt
        # verbose=False unterdrückt Konsolenausgaben für Performance
        results = self.model(frame, verbose=False, conf=config.CONFIDENCE_THRESHOLD)
        detected_objects = []
        
        if not results: return []
        
        result = results[0] # Wir verarbeiten nur das erste Bild (Batch Size 1)
        
        # Iteration über alle gefundenen Bounding Boxes
        for box in result.boxes:
            # Koordinaten extrahieren (xyxy Format -> xywh Format)
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
            
            x = int(x1)
            y = int(y1)
            w = int(x2 - x1)
            h = int(y2 - y1)
            
            conf = float(box.conf[0])
            cls_id = int(box.cls[0])
            
            # Klassen-Label auflösen (z.B. 0 -> "person")
            if hasattr(result, 'names'):
                label = result.names[cls_id]
            else:
                label = "unknown"

            # ---------- Semantischer Filter ----------
            # Whitelist-Ansatz: Nur definierte Objekte werden weiterverarbeitet.
            # Trick: 'sports ball' wird oft für runde Objekte (Papierkugel) genutzt.
            TARGET_CLASSES = ["bottle", "cup", "can", "sports ball", "orange", "apple"]

            if label.lower() not in TARGET_CLASSES:
                continue

            # ---------- Geometrische Filter ----------
            # 1. Rauschunterdrückung: Zu kleine Boxen ignorieren
            if w < 20 or h < 20:
                continue

            # 2. Rand-Unterdrückung: Objekte, die den Bildrand berühren,
            # sind oft unvollständig und führen zu schlechten Tracking-Ergebnissen.
            margin = 5
            if x < margin or y < margin or (x + w) > (img_w - margin) or (y + h) > (img_h - margin):
                continue
            
            detected_objects.append({
                "label": label,
                "box": (x, y, w, h),
                "conf": conf
            })
            
        return detected_objects
