# tracker_logic.py
"""
Tracking-Backend / State Management.

Zweck
-----
Diese Datei stellt die zeitliche Kohärenz (Temporal Coherence) zwischen einzelnen
Video-Frames her. Während YOLO nur "Momentaufnahmen" liefert, sorgt dieses Modul dafür,
dass ein Objekt über die Zeit hinweg eine feste ID behält.

Kern-Algorithmus (Centroid Tracking):
1.  Berechnung der euklidischen Distanzen zwischen allen bekannten Objekten (aus Frame t-1)
    und neuen Detektionen (aus Frame t).
2.  Greedy-Matching: Die kürzesten Distanzen werden zuerst verknüpft.
3.  Lebenszyklus-Management:
    - NEW: Keine passende alte ID gefunden -> Neue ID vergeben.
    - UPDATE: Passende ID gefunden -> Position aktualisieren.
    - MEMORY (Occlusion Handling): Objekt kurzzeitig weg -> Position "einfrieren" und warten.
    - LOST: Objekt zu lange weg oder aus dem Bildrand gefahren -> ID löschen.

Design-Notizen
--------------
- I/O-Optimierung: Das Schreiben in die JSON-Logdatei ist gedrosselt (Buffer), 
  um die Framerate des Roboters nicht durch Festplattenzugriffe zu bremsen.
- Heuristik "Kill Zone": Objekte, die den Bildrand berühren, werden sofort gelöscht,
  da Tracking am Rand unzuverlässig ist (Objekt nur halb sichtbar).
"""

import json
import time
import math
import os
from datetime import datetime
from config import MEMORY_TOLERANCE, BORDER_MARGIN, MAX_TRACKING_DISTANCE, HISTORY_DURATION, RECOVERY_DISTANCE

class TrackedObject:
    """
    Datencontainer für ein einzelnes Objekt.
    Speichert den Zustand (Position, ID, Zeitstempel, Status).
    """
    def __init__(self, uid, label, box, original_start_time=None):
        self.uid = uid
        self.label = label
        self.box = box # Format: (x, y, w, h)
        
        # Zeitstempel für Statistiken
        if original_start_time:
            self.start_time = original_start_time
        else:
            self.start_time = time.time()
            
        self.first_seen_str = datetime.fromtimestamp(self.start_time).strftime("%Y-%m-%d %H:%M:%S")
        self.last_seen_time = time.time()
        
        # Tracking-Metriken
        self.missing_frames = 0 # Zähler für Occlusion (Verdeckung)
        self.active = True      # True = Im aktuellen Frame sichtbar

    def update(self, box):
        """Wird aufgerufen, wenn das Objekt im aktuellen Frame wiedererkannt wurde."""
        self.box = box
        self.last_seen_time = time.time()
        self.missing_frames = 0
        self.active = True

    def mark_missing(self):
        """Wird aufgerufen, wenn das Objekt temporär unsichtbar ist."""
        self.missing_frames += 1
        self.active = False
    
    def get_duration_string(self):
        """Hilfsfunktion für die GUI-Anzeige."""
        elapsed = time.time() - self.start_time
        minutes = int(elapsed // 60)
        seconds = int(elapsed % 60)
        return f"{minutes:02}:{seconds:02}"

class ObjectManager:
    """
    Verwaltet die Liste aller aktiven und historischen Objekte.
    Implementiert die Matching-Logik.
    """
    def __init__(self, json_path):
        self.json_path = json_path
        self.entities = {} # Aktive Objekte {uid: TrackedObject}
        self.history = {}  # "Friedhof" / Gedächtnis für kurzzeitig verlorene Objekte
        self.next_uid = 1  # Auto-Increment ID
        
        # Performance: JSON nicht jeden Frame schreiben
        self.last_json_write = 0
        self.write_interval = 2.0  # Nur alle 2 Sekunden schreiben
        
        self.ensure_json_exists()

    def ensure_json_exists(self):
        """Initialisiert die Log-Datei, falls nicht vorhanden."""
        folder = os.path.dirname(self.json_path)
        if folder and not os.path.exists(folder):
            os.makedirs(folder, exist_ok=True)
        if not os.path.exists(self.json_path):
            self.write_json([])

    def write_json(self, data_list):
        """Schreibt Tracking-Daten persistent auf die Disk."""
        try:
            with open(self.json_path, 'w') as f:
                json.dump(data_list, f, indent=4)
            os.chmod(self.json_path, 0o666) # Lese-/Schreibrechte für alle User (Debugging)
        except Exception as e:
            print(f"JSON Fehler: {e}")

    def is_in_kill_zone(self, box, img_w, img_h):
        """
        Prüft, ob ein Objekt den Bildrand berührt.
        Rand-Objekte werden oft falsch erkannt oder verschwinden gleich -> Löschen.
        """
        x, y, w, h = box
        if x < BORDER_MARGIN or y < BORDER_MARGIN: return True
        if (x + w) > (img_w - BORDER_MARGIN) or (y + h) > (img_h - BORDER_MARGIN): return True
        return False

    def calculate_distance(self, box1, box2):
        """
        Berechnet die Distanz zwischen zwei Objekt-Mittelpunkten (Zentroiden).
        Grundlage für die Entscheidung "Ist Objekt A == Objekt B?".
        """
        c1_x, c1_y = box1[0] + box1[2]/2, box1[1] + box1[3]/2
        c2_x, c2_y = box2[0] + box2[2]/2, box2[1] + box2[3]/2
        return math.hypot(c2_x - c1_x, c2_y - c1_y)

    def process(self, detected_objects, img_w, img_h):
        """
        Haupt-Update-Schleife des Trackers.
        Hier passiert die Magie der Daten-Assoziation.
        """
        current_time = time.time()
        
        # --- 1. MATCHING VORBEREITUNG (Kostenmatrix erstellen) ---
        # Wir berechnen ALLE möglichen Distanzen zwischen alten IDs und neuen Boxen.
        active_uids = list(self.entities.keys())
        matches = [] # Liste von Tupeln: (Distanz, uid, detection_index)

        for uid in active_uids:
            entity = self.entities[uid]
            for i, obj in enumerate(detected_objects):
                # Hard Constraint: Ein Apfel kann nicht plötzlich zur Banane werden.
                if entity.label == obj['label']:
                    dist = self.calculate_distance(entity.box, obj['box'])
                    # Gating: Wenn Distanz zu groß (Sprung), ist es wohl ein anderes Objekt.
                    if dist < MAX_TRACKING_DISTANCE:
                        matches.append((dist, uid, i))
        
        # --- 2. GREEDY MATCHING ---
        # Sortieren nach kleinster Distanz. Das naheliegendste Match gewinnt.
        # Dies ist eine einfache, aber schnelle Alternative zum "Ungarischen Algorithmus".
        matches.sort(key=lambda x: x[0])
        
        matched_uids = set()
        matched_indices = set()

        # Zuweisung durchführen
        for dist, uid, i in matches:
            if uid in matched_uids or i in matched_indices:
                continue # Dieses Paar ist schon vergeben
            
            # Match akzeptiert: Objekt-Position aktualisieren
            self.entities[uid].update(detected_objects[i]['box'])
            matched_uids.add(uid)
            matched_indices.add(i)

        # --- 3. WIEDERBELEBUNG (Recovery) & NEUERSTELLUNG ---
        for i, obj in enumerate(detected_objects):
            if i in matched_indices:
                continue # Wurde bereits einem aktiven Objekt zugeordnet

            # Objekt konnte keinem aktiven Tracker zugeordnet werden.
            # Ist es vielleicht ein altes Objekt, das kurz verdeckt war?
            new_box = obj['box']
            new_label = obj['label']
            
            best_history_uid = None
            min_hist_dist = RECOVERY_DISTANCE
            
            # Suche im "Gedächtnis" (History)
            history_uids = list(self.history.keys())
            for h_uid in history_uids:
                h_entity = self.history[h_uid]
                if h_entity.label != new_label: continue
                
                dist = self.calculate_distance(h_entity.box, new_box)
                if dist < min_hist_dist:
                    min_hist_dist = dist
                    best_history_uid = h_uid

            if best_history_uid is not None:
                # RE-IDENTIFICATION: Objekt wiedergefunden -> Zurück in aktive Liste
                old_entity = self.history.pop(best_history_uid)
                print(f">>> RESURRECT: ID #{best_history_uid} ({new_label}) wieder da!")
                resurrected = TrackedObject(old_entity.uid, new_label, new_box, old_entity.start_time)
                self.entities[best_history_uid] = resurrected
            else:
                # NEW: Wirklich neues Objekt -> Neue ID vergeben
                print(f">>> NEUES OBJEKT ID #{self.next_uid}: {new_label}")
                self.entities[self.next_uid] = TrackedObject(self.next_uid, new_label, new_box)
                self.next_uid += 1

        # --- 4. AUFRÄUMEN (Lost & Kill Zone) ---
        # Was passiert mit Objekten, die im aktuellen Frame NICHT gesehen wurden?
        codes_to_move_to_history = []
        current_active_uids = list(self.entities.keys())

        for uid in current_active_uids:
            if uid in matched_uids:
                continue # Alles gut, wurde geupdatet

            # Objekt fehlt im aktuellen Bild
            entity = self.entities[uid]
            entity.mark_missing()
            
            # Entscheidung: Löschen oder Merken?
            if self.is_in_kill_zone(entity.box, img_w, img_h):
                # Wenn es am Rand verschwindet, gehen wir davon aus, dass es weg ist.
                print(f"<<< RAND-KILL: ID #{uid}")
                codes_to_move_to_history.append((uid, False)) # False = nicht in History speichern
            elif entity.missing_frames > MEMORY_TOLERANCE:
                # Wenn es zu lange fehlt (Timeout), schieben wir es ins Langzeit-Gedächtnis.
                print(f"<<< TIMEOUT: ID #{uid}")
                codes_to_move_to_history.append((uid, True))  # True = in History speichern

        # Verschieben/Löschen durchführen
        for uid, keep_in_history in codes_to_move_to_history:
            if keep_in_history:
                self.history[uid] = self.entities[uid]
            del self.entities[uid]

        # --- 5. GARBAGE COLLECTION ---
        # Alte Einträge aus der History löschen, um Speicherüberlauf zu verhindern
        history_to_delete = []
        for uid, entity in self.history.items():
            if (current_time - entity.last_seen_time) > HISTORY_DURATION:
                history_to_delete.append(uid)
        for uid in history_to_delete:
            del self.history[uid]

        # --- 6. JSON EXPORT ---
        # Status für Web-Interface oder Logs schreiben
        if current_time - self.last_json_write > self.write_interval:
            json_output = []
            for uid, entity in self.entities.items():
                json_output.append({
                    "internal_id": uid,
                    "class": entity.label,
                    "duration": entity.get_duration_string(),
                    "timestamp": entity.first_seen_str,
                    "status": "LIVE" if entity.active else "MEMORY"
                })
            self.write_json(json_output)
            self.last_json_write = current_time
        
        return self.entities
