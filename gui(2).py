import cv2
from config import BORDER_MARGIN

def draw_overlay(frame, width, height, active_entities):
    # Kill Zone
    cv2.rectangle(frame, 
                  (BORDER_MARGIN, BORDER_MARGIN), 
                  (width - BORDER_MARGIN, height - BORDER_MARGIN), 
                  (0, 0, 255), 3)
    cv2.putText(frame, "EXIT ZONE", (10, BORDER_MARGIN - 10), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

    # Objekte
    for entity in active_entities.values():
        draw_entity(frame, entity)

    # Info
    cv2.putText(frame, f"Objects: {len(active_entities)}", (30, 50), 
                cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 0), 3)
    cv2.putText(frame, f"Res: {width}x{height}", (30, height - 30), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

def draw_entity(frame, entity):
    x, y, w, h = entity.box
    color = (0, 255, 0) if entity.active else (0, 165, 255)
    thickness = 4 if entity.active else 2
    
    cv2.rectangle(frame, (x, y), (x + w, y + h), color, thickness)
    
    # Text: "#1 Papierkugel (00:12)"
    text_line1 = f"#{entity.uid} {entity.label}"
    text_line2 = f"Time: {entity.get_duration_string()}"
    if not entity.active: text_line1 += " (?)"

    tx, ty = x, y - 10
    
    cv2.putText(frame, text_line1, (tx, ty), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 8)
    cv2.putText(frame, text_line1, (tx, ty), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
    
    cv2.putText(frame, text_line2, (tx, ty - 35), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 6)
    cv2.putText(frame, text_line2, (tx, ty - 35), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
