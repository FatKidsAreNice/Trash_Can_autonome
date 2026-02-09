# gui.py
"""
Visualisierungsschicht / Overlay Rendering.

Zweck
-----
Zeichnet Tracking-Informationen direkt in den Video-Frame (In-Place Modification).
Dient als Human-Machine-Interface (HMI) für Entwickler, um zu sehen:
1. Was sieht die KI? (Bounding Boxes)
2. Was denkt der Tracker? (IDs, History)
3. Wo sind die Grenzen? (Exit Zone)

Design-Notizen
--------------
- Nutzt OpenCV (cv2) Zeichenfunktionen.
- Visuelles Feedback durch Farben:
  - Grün: Aktives Tracking (Objekt ist sichtbar).
  - Orange/Dünn: "Geister"-Objekt (gerade verloren/aus dem Gedächtnis).
"""

import cv2
from config import BORDER_MARGIN

def draw_overlay(frame, width, height, active_entities):
    """
    Hauptfunktion zum Zeichnen des Overlays.
    Wird einmal pro Frame am Ende der Pipeline aufgerufen.
    """
    
    # --- 1. Exit Zone (Kill Zone) visualisieren ---
    # Hilft dem User zu verstehen, warum ein Objekt am Rand "stirbt".
    cv2.rectangle(frame, 
                  (BORDER_MARGIN, BORDER_MARGIN), 
                  (width - BORDER_MARGIN, height - BORDER_MARGIN), 
                  (0, 0, 255), 3) # Roter Rahmen
    cv2.putText(frame, "EXIT ZONE", (10, BORDER_MARGIN - 10), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

    # --- 2. Entitäten zeichnen ---
    for entity in active_entities.values():
        draw_entity(frame, entity)

    # --- 3. HUD (Heads-Up Display) ---
    # Globale Statistiken oben links und unten links.
    cv2.putText(frame, f"Objects: {len(active_entities)}", (30, 50), 
                cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 0), 3)
    cv2.putText(frame, f"Res: {width}x{height}", (30, height - 30), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

def draw_entity(frame, entity):
    """
    Zeichnet Box und Label für ein einzelnes Objekt.
    Unterscheidet visuell zwischen "aktiv" und "verloren".
    """
    x, y, w, h = entity.box
    
    # Visuelle Kodierung des Status
    if entity.active:
        color = (0, 255, 0) # Grün = Alles OK
        thickness = 4
    else:
        color = (0, 165, 255) # Orange = Warnung (Objekt aktuell unsichtbar)
        thickness = 2
    
    # Bounding Box
    cv2.rectangle(frame, (x, y), (x + w, y + h), color, thickness)
    
    # Label-Aufbau: "#1 Papierkugel (00:12)"
    text_line1 = f"#{entity.uid} {entity.label}"
    text_line2 = f"Time: {entity.get_duration_string()}"
    
    # Markierung für unsichere Objekte
    if not entity.active: text_line1 += " (?)"

    tx, ty = x, y - 10
    
    # Text mit Outline (schwarzer Rand) für bessere Lesbarkeit auf hellem Hintergrund
    cv2.putText(frame, text_line1, (tx, ty), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 8) # Outline
    cv2.putText(frame, text_line1, (tx, ty), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)     # Text
    
    cv2.putText(frame, text_line2, (tx, ty - 35), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 6)
    cv2.putText(frame, text_line2, (tx, ty - 35), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
