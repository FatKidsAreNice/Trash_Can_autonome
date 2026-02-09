import serial
import time

# Konfiguration (wie in deinem main.py)
PORT = '/dev/ttyACM0'
BAUD = 9600

def send_command(arduino, throttle, steering):
    """
    Sendet den Befehl im Format <GAS,LENKUNG> an den Arduino.
    Werte sollten floats sein (z.B. 0.50).
    """
    # Formatierung exakt wie in main.py
    cmd = f"<{throttle:.2f},{steering:.2f}>\n"
    print(f"Sende: {cmd.strip()}")
    arduino.write(cmd.encode())

def test_sequence():
    print(f"--- STARTE MOTOR TEST (Port: {PORT}) ---")
    
    try:
        # Verbindung öffnen
        arduino = serial.Serial(PORT, BAUD, timeout=1)
        
        # WICHTIG: Wenn der Serial Port geöffnet wird, startet der Arduino neu.
        # Wir müssen kurz warten, bis er bereit ist.
        print("Warte 2 Sekunden auf Arduino-Reset...")
        time.sleep(2)
        print("Bereit!")

        # 1. KURZ VORWÄRTS (30% Gas)
        print("\nTEST 1: Vorwärts (30%)")
        send_command(arduino, 0.3, 0.0)
        time.sleep(1.5) # 1,5 Sekunden fahren

        # 2. STOPP
        print("Stopp")
        send_command(arduino, 0.0, 0.0)
        time.sleep(1)

        # 3. LINKS LENKEN (im Stand oder mit wenig Gas, je nach Roboter-Logik)
        # Wir geben etwas Gas dazu, damit man die Drehung sieht
        print("\nTEST 2: Links kurven")
        send_command(arduino, 0.3, -1.0) 
        time.sleep(1.5)

        # 4. STOPP
        print("Stopp")
        send_command(arduino, 0.0, 0.0)
        time.sleep(1)

        # 5. RECHTS LENKEN
        print("\nTEST 3: Rechts kurven")
        send_command(arduino, 0.3, 1.0)
        time.sleep(1.5)

        # ENDE: Alles aus
        print("\n--- TEST ENDE (Motoren aus) ---")
        send_command(arduino, 0.0, 0.0)
        arduino.close()

    except serial.SerialException as e:
        print(f"\nFEHLER: Konnte nicht verbinden: {e}")
        print("Tipp: Hast du 'sudo chmod 666 /dev/ttyACM0' ausgeführt?")
    except KeyboardInterrupt:
        print("\nAbbruch durch Benutzer!")
        if 'arduino' in locals() and arduino.is_open:
            send_command(arduino, 0.0, 0.0)
            arduino.close()

if __name__ == "__main__":
    test_sequence()
