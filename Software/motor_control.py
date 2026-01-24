import serial
import json
import time

# --- CONFIGURATION ---
# Mac: ls /dev/tty.usbmodem* # Windows: Check Device Manager (COMx)
SENSOR_PORT = '/dev/cu.usbmodem12134239842' # Arduino Uno Q
MOTOR_PORT = '/dev/cu.usbmodem101'  # The ESP32-S3
BAUD_RATE   = 115200

THRESHOLD_GSR = 500  # Adjust based on baseline
COOLDOWN = 4.0       # Seconds between vibrations

def main():
    try:
        print(f"Connecting to Sensors on {SENSOR_PORT}...")
        sensor_ser = serial.Serial(SENSOR_PORT, BAUD_RATE, timeout=1)
        
        print(f"Connecting to Motor on {MOTOR_PORT}...")
        motor_ser = serial.Serial(MOTOR_PORT, BAUD_RATE, timeout=1)
        
        print("✅ BRIDGE ACTIVE. Waiting for bio-data...")
        
        last_trigger_time = 0

        while True:
            # 1. Read line from Uno Q
            if sensor_ser.in_waiting > 0:
                raw_line = sensor_ser.readline().decode('utf-8').strip()
                
                # Filter out debug messages, look for JSON
                if raw_line.startswith('{') and raw_line.endswith('}'):
                    try:
                        data = json.loads(raw_line)
                        gsr_val = data.get('gsr', 0)
                        pulse_val = data.get('pulse', 0)
                        
                        print(f"GSR: {gsr_val} | Pulse: {pulse_val}")

                        # 2. Logic: If GSR spikes, trigger Motor
                        if gsr_val > THRESHOLD_GSR:
                            if time.time() - last_trigger_time > COOLDOWN:
                                print(">>> TRIGGERING MOTOR! <<<")
                                motor_ser.write(b'1') # Send '1' to ESP32
                                last_trigger_time = time.time()
                                
                    except json.JSONDecodeError:
                        pass # Ignore partial lines

    except serial.SerialException as e:
        print(f"\n❌ Port Error: {e}")
        print("Check your connections and port names.")

if __name__ == "__main__":
    main()