import serial
import json
import time

# --- CONFIGURATION ---
# REPLACE THIS with your actual port from the Arduino IDE (bottom right corner)
SERIAL_PORT = "/dev/cu.usbmodem12134239842"  
BAUD_RATE = 115200

def main():
    print(f"Connecting to Uno Q on {SERIAL_PORT}...")

    try:
        # Open the Serial Port
        # timeout=1 prevents the script from freezing if the board is silent
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        time.sleep(2) # Wait for the connection to stabilize
        print("Connected! Waiting for data...")

        while True:
            if ser.in_waiting > 0:
                try:
                    # 1. Read the raw line from USB
                    raw_line = ser.readline().decode('utf-8').strip()
                    
                    # 2. Filter out non-JSON noise (like boot messages)
                    if raw_line.startswith("{") and raw_line.endswith("}"):
                        
                        # 3. Parse the JSON
                        data = json.loads(raw_line)
                        
                        # 4. Extract Variables
                        gsr = data.get("gsr", 0)
                        pulse = data.get("pulse", 0)
                        
                        # --- YOUR LOGIC GOES HERE ---
                        # Example: Print nicely formatted data
                        print(f"BPM Raw: {pulse} | GSR: {gsr}")
                        
                        # Next step: Send 'gsr' to Gemini API here!
                        
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