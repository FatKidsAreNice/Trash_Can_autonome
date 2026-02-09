# motor_test.py
"""
Hardware-Unit-Test für den Antriebsstrang.

Zweck
-----
Dient zur Isolierung von Fehlern. Bevor die KI läuft, muss sichergestellt sein,
dass:
1. Der Arduino über USB (/dev/ttyACM0) erreichbar ist.
2. Das Kommunikationsprotokoll korrekt interpretiert wird.
3. Die Motoren physikalisch drehen (Verkabelung prüfen).

Ablauf
------
Führt eine feste Choreografie aus: Vorwärts -> Stopp -> Links -> Stopp -> Rechts.
"""

import serial
import time

# Port-Konfiguration
PORT = '/dev/ttyACM0'
BAUD = 9600

def send_command(arduino, throttle, steering):
    """
    Kapselt das Kommunikationsprotokoll.
    Protokoll: Startbyte '<', Daten, Endbyte '>' -> z.B. "<0.50,-1.00>"
    """
    cmd = f"<{throttle:.2f},{steering:.2f}>\n"
    print(f"Sende: {cmd.strip()}")
    arduino.write(cmd.encode())

def test_sequence():
    print(f"--- STARTE MOTOR TEST (Port: {PORT}) ---")
    
    try:
        # Serial Handshake
        arduino = serial.Serial(PORT, BAUD, timeout=1)
        
        # WICHTIG: DTR-Reset abwarten. Arduino startet neu bei Serial-Verbindung.
        print("Warte 2 Sekunden auf Arduino-Reset...")
        time.sleep(2)
        print("Bereit!")

        # --- Test-Choreografie ---
        
        # 1. Traktionstest (Vorwärts)
        print("\nTEST 1: Vorwärts (30%)")
        send_command(arduino, 0.3, 0.0)
        time.sleep(1.5) 

        # 2. Totzeit (Safety)
        print("Stopp")
        send_command(arduino, 0.0, 0.0)
        time.sleep(1)

        # 3. Lenktest Links (Differential Drive oder Servo)
        print("\nTEST 2: Links kurven")
        send_command(arduino, 0.3, -1.0) 
        time.sleep(1.5)

        # 4. Totzeit
        print("Stopp")
        send_command(arduino, 0.0, 0.0)
        time.sleep(1)

        # 5. Lenktest Rechts
        print("\nTEST 3: Rechts kurven")
        send_command(arduino, 0.3, 1.0)
        time.sleep(1.5)

        # Safety Shutdown am Ende
        print("\n--- TEST ENDE (Motoren aus) ---")
        send_command(arduino, 0.0, 0.0)
        arduino.close()

    except serial.SerialException as e:
        print(f"\nFEHLER: Konnte nicht verbinden: {e}")
        print("Tipp: Hast du 'sudo chmod 666 /dev/ttyACM0' ausgeführt?")
    except KeyboardInterrupt:
        # Failsafe bei manuellem Abbruch
        print("\nAbbruch durch Benutzer!")
        if 'arduino' in locals() and arduino.is_open:
            send_command(arduino, 0.0, 0.0)
            arduino.close()

if __name__ == "__main__":
    test_sequence()
