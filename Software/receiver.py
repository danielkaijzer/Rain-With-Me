import serial
import json
import time
import socket

# --- CONFIGURATION ---
SERIAL_PORT = "/dev/cu.usbmodem12134239842"  
BAUD_RATE = 115200

# Unity Connection Info
UDP_IP = "127.0.0.1" # Localhost (Your computer)
UDP_PORT = 5005      # The port Unity will listen to

def main():
    # Setup UDP Socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    print(f"Connecting to Uno Q on {SERIAL_PORT}...")
    print(f"Broadcasting to Unity on {UDP_IP}:{UDP_PORT}")

    try:
        # Open the Serial Port
        # timeout=1 prevents the script from freezing if the board is silent
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        time.sleep(2) # Wait for the connection to stabilize
        print("Connected! Waiting for data...")

        while True:
            if ser.in_waiting > 0:
                try:
                    # Read the raw line from USB
                    raw_line = ser.readline().decode('utf-8').strip()
                    
                    # Filter out non-JSON noise (like boot messages)
                    if raw_line.startswith("{") and raw_line.endswith("}"):
                        
                        # Parse the JSON
                        arduino_data = json.loads(raw_line)

                        sock.sendto(raw_line.encode(), (UDP_IP, UDP_PORT))
                        
                        # Extract Variables (Will do some pre-processing on this later)
                        val1 = arduino_data.get("gsr", 0)
                        val2 = arduino_data.get("pulse", 0)

                        unity_payload = {
                            "sensor_1": val1,  # Currently GSR
                            "sensor_2": val2   # Currently Pulse
                        }

                        # TRANSMIT: Send to Unity
                        message = json.dumps(unity_payload).encode()
                        sock.sendto(message, (UDP_IP, UDP_PORT))
                        
                        print(f"BPM Raw: {val2} | GSR: {val1}")
                        
                except json.JSONDecodeError:
                    pass # Ignore partial/corrupt lines
                except UnicodeDecodeError:
                    pass # Ignore garbage characters

    except serial.SerialException as e:
        print(f"\nERROR: Could not open {SERIAL_PORT}")
        print(" TIP: Is the Arduino IDE Serial Monitor still open? CLOSE IT!")
        print(f"Details: {e}")
    except KeyboardInterrupt:
        print("\nStopping...")
        if 'ser' in locals():
            ser.close()

if __name__ == "__main__":
    main()