import socket
import json
import time
import serial

# --- CONFIGURATION ---
UDP_IP = "127.0.0.1"
UDP_PORT = 5006
MOTOR_PORT = 5015
MOTOR_PORT = 'COM4' 
BAUD_RATE = 115200

# Updates motor at most 10 times a second (10Hz) to prevent serial clogging
UPDATE_RATE = 0.1 

def main():
    try:
        print(f"Connecting to Rain ESP32 on {MOTOR_PORT}...")
        motor_ser = serial.Serial(MOTOR_PORT, BAUD_RATE, timeout=1)
        time.sleep(2)
        print("ESP32 Connected.")
    except serial.SerialException as e:
        print(f"❌ Error: {e}")
        return

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT))
    print(f"Rain Simulator Active on UDP {UDP_PORT}")

    last_update_time = 0

    while True:
        try:
            data_bytes, addr = sock.recvfrom(1024) 
            raw_json = data_bytes.decode('utf-8')

            try:
                data = json.loads(raw_json)
                
                # Get Normalized GSR (0.0 - 1.0)
                # If your bridge sends 0-100 ints, divide by 100 here!
                current_gsr = data.get("final_arousal", data.get("final_arousal", 0))
                
                # Rate Limit the Serial Writes
                if time.time() - last_update_time > UPDATE_RATE:
                    
                    # DIRECT MAPPING: 0.0 -> 0, 1.0 -> 255
                    intensity_float = max(0.0, min(1.0, float(current_gsr)))
                    # intensity_float = round(intensity_float * 20) / 20.0 # Optional to help with ramping 
                    intensity_byte = int(intensity_float * 255)

                    # Send to ESP32
                    motor_ser.write(bytes([intensity_byte]))
                    
                    print(f"GSR: {intensity_float:.2f} -> Rain Intensity: {intensity_byte}")
                    
                    last_update_time = time.time()

            except json.JSONDecodeError:
                pass

        except KeyboardInterrupt:
            print("\nStopping...")
            break
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()