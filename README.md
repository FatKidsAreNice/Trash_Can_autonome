# Trash_Can_autonome
KI-basierter Autonomer Verfolgungs-Roboter (AI Object Tracker)

Dieses Projekt implementiert ein autonomes Robotersystem, das in der Lage ist, spezifische Objekte (z. B. Flaschen, Bälle) in Echtzeit zu erkennen und ihnen physikalisch zu folgen. Das System kombiniert Computer Vision (YOLO) auf einem Edge-Device (Nvidia Jetson) mit einer Mikrocontroller-basierten Motorsteuerung (Arduino).

# Systemarchitektur

Das System folgt einem klassischen Sense-Think-Act-Paradigma, verteilt auf zwei Hardware-Ebenen:

  1.  High-Level Computing (Nvidia Jetson):

       - Wahrnehmung: Bildaufnahme und Objekterkennung mittels Deep Learning (YOLOv8/11).

       - Logik: Objekt-Tracking (Identitätserhaltung) und Bewegungsplanung.

       - Kommunikation: Sendet Steuerbefehle (Gas, Lenkung) via USB (Serial) an den Arduino.

  2. Low-Level Control (Arduino):

       - Empfängt Steuervektoren im Format <THROTTLE, STEERING>.

       - Wandelt Vektoren in PWM-Signale für die Motortreiber um.

 # Hardware-Anforderungen

   - Recheneinheit: Nvidia Jetson Nano / Orin Nano (für GPU-beschleunigte Inferenz).

   - Kamera: Arducam IMX519 oder vergleichbare CSI/USB-Kamera mit Fokus-Steuerung.

   - Mikrocontroller: Arduino Uno/Nano (verbunden via USB /dev/ttyACM0).

   - Aktorik: Roboter-Chassis mit DC-Motoren und Motortreiber.

# Software-Module

Das Projekt ist modular aufgebaut, um Wartbarkeit und Austauschbarkeit zu gewährleisten:
Datei	Beschreibung

- main.py	Einstiegspunkt. Initialisiert Hardware, startet den Main-Loop und synchronisiert Vision und Aktorik.
  
- yolo_detector.py	Perzeption. Wrapper für das YOLO-Modell. Filtert Ergebnisse nach Klasse, Konfidenz und Randbereich.
  
- tracker_logic.py	Gedächtnis. Implementiert Centroid Tracking. Ordnet neuen Detektionen IDs zu und speichert verlorene Objekte kurzzeitig in einer History.
  
- robot_brain.py	Regelung. Berechnet Lenkwinkel (P-Regler) und Geschwindigkeit basierend auf der Position und Größe des Zielobjekts.
  
- config.py	Konfiguration. Zentrale Datei für Konstanten, Pfade und Tuning-Parameter.
  
- gui.py	Visualisierung. Zeichnet Bounding Boxes, Status-Infos und die "Exit Zone" zur Fehleranalyse in das Videobild.
  
- motor_test.py	Diagnose. Standalone-Skript zum Testen der seriellen Verbindung und der Motoren.


# Algorithmische Details

1. Objekterkennung & Filterung

Das System nutzt ein vortrainiertes YOLO-Modell (bevorzugt .engine Format für TensorRT).

   - Semantischer Filter: Nur relevante Klassen (z. B. "bottle", "sports ball") werden akzeptiert.

   - Geometrischer Filter: Objekte, die zu klein sind oder den Bildrand berühren, werden ignoriert, um Fehlsteuerungen zu vermeiden.

2. Zeitliche Kohärenz (Tracking)

Da YOLO keine IDs liefert, nutzt tracker_logic.py einen euklidischen Distanz-Algorithmus:

   - Matching: Verknüpft die Detektion in Frame t mit dem Objekt in Frame t−1, wenn die Distanz < MAX_TRACKING_DISTANCE ist.

   - Objekt-Permanenz: Verschwindet ein Objekt (Verdeckung), wird es für HISTORY_DURATION (z.B. 5s) im Speicher gehalten ("Ghost"-Objekt). Taucht es an ähnlicher Stelle wieder auf, erhält es seine alte ID zurück.

3. Bewegungssteuerung

Der RobotBrain nutzt einen einfachen Regelkreis:

   - Lenkung: Proportional zur Abweichung der Objektmitte von der Bildmitte (error_x).

   - Gas: Abhängig von der Objektgröße (Distanz). Ist das Objekt kleiner als TARGET_WIDTH_RATIO (40% Bildbreite), nähert sich der Roboter an.

# Installation & Nutzung
Voraussetzungen

   1. Python 3.8+

   2. Installierte Bibliotheken:
    Bash

    pip install ultralytics opencv-python pyserial numpy

   3. Ein exportiertes YOLO-Modell im Projektordner (definiert in config.py).

Starten des Systems

   1. Hardware-Test: Stellen Sie sicher, dass der Arduino verbunden ist.
    Bash

    python3 motor_test.py

    Hauptprogramm: Starten Sie den Tracker mit Angabe des I2C-Bus für den Fokus.
    Bash

    sudo python3 main.py -i 9

Steuerung

   - q: Programm beenden.

   - f: Autofokus manuell triggern.

 # Konfiguration (config.py)

Wichtige Tuning-Parameter für Anpassungen an die Umgebung:

   - SCALE_FACTOR: Skalierung des Eingangsbildes (z.B. 0.8) für schnellere Inferenz.

   - CONFIDENCE_THRESHOLD: Ab welcher Sicherheit (0.0 - 1.0) ein Objekt erkannt wird.

   - MEMORY_TOLERANCE: Wie viele Frames ein Objekt fehlen darf, bevor es in den "Lost"-Status übergeht.

   - MODEL_PATH: Pfad zur Modelldatei (.pt oder .engine).
