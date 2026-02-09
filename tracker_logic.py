import json
import time
import math
import os
from datetime import datetime
from config import MEMORY_TOLERANCE, BORDER_MARGIN, MAX_TRACKING_DISTANCE, HISTORY_DURATION, RECOVERY_DISTANCE

class TrackedObject:
    def __init__(self, uid, label, box, original_start_time=None):
        self.uid = uid
        self.label = label
        self.box = box
        
        if original_start_time:
            self.start_time = original_start_time
        else:
            self.start_time = time.time()
            
        self.first_seen_str = datetime.fromtimestamp(self.start_time).strftime("%Y-%m-%d %H:%M:%S")
        self.last_seen_time = time.time()
        self.missing_frames = 0
        self.active = True

    def update(self, box):
        self.box = box
        self.last_seen_time = time.time()
        self.missing_frames = 0
        self.active = True

    def mark_missing(self):
        self.missing_frames += 1
        self.active = False
    
    def get_duration_string(self):
        elapsed = time.time() - self.start_time
        minutes = int(elapsed // 60)
        seconds = int(elapsed % 60)
        return f"{minutes:02}:{seconds:02}"

class ObjectManager:
    def __init__(self, json_path):
        self.json_path = json_path
        self.entities = {} 
        self.history = {}
        self.next_uid = 1 
        
        # I/O Optimierung
        self.last_json_write = 0
        self.write_interval = 2.0  # Sekunden
        
        self.ensure_json_exists()

    def ensure_json_exists(self):
        folder = os.path.dirname(self.json_path)
        if folder and not os.path.exists(folder):
            os.makedirs(folder, exist_ok=True)
        if not os.path.exists(self.json_path):
            self.write_json([])

    def write_json(self, data_list):
        try:
            with open(self.json_path, 'w') as f:
                json.dump(data_list, f, indent=4)
            # Berechtigungen setzen, damit User es lesen kann
            os.chmod(self.json_path, 0o666)
        except Exception as e:
            print(f"JSON Fehler: {e}")

    def is_in_kill_zone(self, box, img_w, img_h):
        x, y, w, h = box
        # Toleranz am Rand etwas lockerer sehen
        if x < BORDER_MARGIN or y < BORDER_MARGIN: return True
        if (x + w) > (img_w - BORDER_MARGIN) or (y + h) > (img_h - BORDER_MARGIN): return True
        return False

    def calculate_distance(self, box1, box2):
        # Euklidische Distanz der Mittelpunkte
        c1_x, c1_y = box1[0] + box1[2]/2, box1[1] + box1[3]/2
        c2_x, c2_y = box2[0] + box2[2]/2, box2[1] + box2[3]/2
        return math.hypot(c2_x - c1_x, c2_y - c1_y)

    def process(self, detected_objects, img_w, img_h):
        current_time = time.time()
        
        # --- 1. MATCHING VORBEREITUNG ---
        # Wir berechnen ALLE möglichen Distanzen zwischen alten IDs und neuen Boxen
        active_uids = list(self.entities.keys())
        matches = [] # Liste von (Distanz, uid, detection_index)

        for uid in active_uids:
            entity = self.entities[uid]
            for i, obj in enumerate(detected_objects):
                # Nur gleiche Klasse darf matchen
                if entity.label == obj['label']:
                    dist = self.calculate_distance(entity.box, obj['box'])
                    if dist < MAX_TRACKING_DISTANCE:
                        matches.append((dist, uid, i))
        
        # Sortieren nach kleinster Distanz (Greedy Matching)
        # Das verhindert, dass ein weit entferntes Objekt eine ID "klaut", 
        # die eigentlich zu einem nahen Objekt gehört.
        matches.sort(key=lambda x: x[0])
        
        matched_uids = set()
        matched_indices = set()

        # --- 2. ZUWEISUNG (Update) ---
        for dist, uid, i in matches:
            if uid in matched_uids or i in matched_indices:
                continue # Schon vergeben
            
            # Update durchführen
            self.entities[uid].update(detected_objects[i]['box'])
            matched_uids.add(uid)
            matched_indices.add(i)

        # --- 3. WIEDERBELEBUNG & NEUE OBJEKTE ---
        for i, obj in enumerate(detected_objects):
            if i in matched_indices:
                continue # Schon als Live-Objekt getrackt

            new_box = obj['box']
            new_label = obj['label']
            
            # Suche im Friedhof (History)
            best_history_uid = None
            min_hist_dist = RECOVERY_DISTANCE
            
            # Auch hier: Greedy wäre besser, aber History ist meist klein genug für Loop
            history_uids = list(self.history.keys())
            for h_uid in history_uids:
                h_entity = self.history[h_uid]
                if h_entity.label != new_label: continue
                
                dist = self.calculate_distance(h_entity.box, new_box)
                if dist < min_hist_dist:
                    min_hist_dist = dist
                    best_history_uid = h_uid

            if best_history_uid is not None:
                # RESURRECT
                old_entity = self.history.pop(best_history_uid)
                print(f">>> RESURRECT: ID #{best_history_uid} ({new_label}) wieder da!")
                resurrected = TrackedObject(old_entity.uid, new_label, new_box, old_entity.start_time)
                self.entities[best_history_uid] = resurrected
            else:
                # NEW
                print(f">>> NEUES OBJEKT ID #{self.next_uid}: {new_label}")
                self.entities[self.next_uid] = TrackedObject(self.next_uid, new_label, new_box)
                self.next_uid += 1

        # --- 4. AUFRÄUMEN (Lost & Kill Zone) ---
        codes_to_move_to_history = []
        # Wir müssen über eine Kopie iterieren, da wir active_uids oben genutzt haben, 
        # aber jetzt den aktuellen Stand brauchen
        current_active_uids = list(self.entities.keys())

        for uid in current_active_uids:
            if uid in matched_uids:
                continue # Wurde gerade aktualisiert

            entity = self.entities[uid]
            entity.mark_missing()
            
            if self.is_in_kill_zone(entity.box, img_w, img_h):
                print(f"<<< RAND-KILL: ID #{uid}")
                codes_to_move_to_history.append((uid, False)) 
            elif entity.missing_frames > MEMORY_TOLERANCE:
                print(f"<<< TIMEOUT: ID #{uid}")
                codes_to_move_to_history.append((uid, True)) 

        for uid, keep_in_history in codes_to_move_to_history:
            if keep_in_history:
                self.history[uid] = self.entities[uid]
            del self.entities[uid]

        # --- 5. FRIEDHOF BEREINIGEN ---
        history_to_delete = []
        for uid, entity in self.history.items():
            if (current_time - entity.last_seen_time) > HISTORY_DURATION:
                history_to_delete.append(uid)
        for uid in history_to_delete:
            del self.history[uid]

        # --- 6. JSON EXPORT (Optimiert) ---
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
