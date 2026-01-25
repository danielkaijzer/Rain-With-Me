import socket
import json
import time
import serial
import select  # Needed to listen to two ports at once

# --- CONFIGURATION ---
UDP_IP = "127.0.0.1"
DATA_PORT = 5006      # Port for GSR/Arousal Data
COMMAND_PORT = 5012   # Port for ON/OFF Commands
MOTOR_PORT = 'COM4'   
BAUD_RATE = 115200

# Updates motor at most 10 times a second (10Hz)
UPDATE_RATE = 0.1 

def main():
    # --- 1. SETUP SERIAL ---
    try:
        print(f"Connecting to Rain ESP32 on {MOTOR_PORT}...")
        motor_ser = serial.Serial(MOTOR_PORT, BAUD_RATE, timeout=1)
        time.sleep(2)
        print("ESP32 Connected.")
    except serial.SerialException as e:
        print(f"❌ Error: {e}")
        return

    # --- 2. SETUP UDP SOCKETS ---
    # Socket A: Listens for Sensor Data (Port 5006)
    data_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    data_sock.bind((UDP_IP, DATA_PORT))
    data_sock.setblocking(False) # Make non-blocking

    # Socket B: Listens for ON/OFF Commands (Port 5012)
    cmd_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    cmd_sock.bind((UDP_IP, COMMAND_PORT))
    cmd_sock.setblocking(False) # Make non-blocking

    print(f"Listening for DATA on {DATA_PORT} and COMMANDS on {COMMAND_PORT}")

    # --- 3. STATE VARIABLES ---
    last_update_time = 0
    motor_enabled = False # Default state (Assumes ON until told otherwise)
    current_gsr = 0.0

    # List of sockets to monitor
    inputs = [data_sock, cmd_sock]

    while True:
        try:
            # --- 4. WAIT FOR DATA ON EITHER PORT ---
            # select.select() waits until one of the sockets has data
            # readable, writable, exceptional = select.select(inputs, [], [])
            readable, _, _ = select.select(inputs, [], [], 0.05) # 0.05s timeout prevents hanging

            for sock in readable:
                
                # CASE A: We received an ON/OFF Command
                if sock is cmd_sock:
                    cmd_data, _ = cmd_sock.recvfrom(1024)
                    command = cmd_data.decode('utf-8').strip().upper()
                    
                    if "OFF" in command:
                        motor_enabled = False
                        print("🚫 COMMAND RECEIVED: MOTOR DISABLED")
                        # Optional: Immediately kill vibration
                        motor_ser.write(bytes([0])) 
                    elif "ON" in command:
                        motor_enabled = True
                        print("✅ COMMAND RECEIVED: MOTOR ENABLED")

                # CASE B: We received Sensor Data
                elif sock is data_sock:
                    data_bytes, _ = data_sock.recvfrom(1024)
                    raw_json = data_bytes.decode('utf-8')
                    try:
                        data = json.loads(raw_json)
                        current_gsr = data.get("final_arousal", 0)
                    except json.JSONDecodeError:
                        pass

            # --- 5. UPDATE MOTOR (Rate Limited) ---
            if time.time() - last_update_time > UPDATE_RATE:
                
                # LOGIC: If motor is disabled, force intensity to 0.0
                if motor_enabled:
                    target_val = float(current_gsr)
                else:
                    target_val = 0.0

                # Clamp 0.0 - 1.0
                intensity_float = max(0.0, min(1.0, target_val))
                
                # Convert to Byte (0-255)
                intensity_byte = int(intensity_float * 255)

                # Send to ESP32
                motor_ser.write(bytes([intensity_byte]))
                
                # Only print if there is significant change or just periodically
                print(f"Enabled: {motor_enabled} | GSR: {intensity_float:.2f} -> Byte: {intensity_byte}")
                
                last_update_time = time.time()

        except KeyboardInterrupt:
            print("\nStopping...")
            break
        except Exception as e:
            print(f"Error in loop: {e}")
            break

    # Cleanup
    motor_ser.close()
    data_sock.close()
    cmd_sock.close()

if __name__ == "__main__":
    main()