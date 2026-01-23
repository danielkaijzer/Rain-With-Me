import serial
import json
import time
import socket
import collections
import statistics

# --- CONFIGURATION ---
SERIAL_PORT = "/dev/cu.usbmodem12134239842"  
BAUD_RATE = 115200

# Unity Connection Info
UDP_IP = "127.0.0.1" # Localhost (Your computer)
UDP_PORT = 5005      # The port Unity will listen to

class BioProcessor:
    def __init__(self):
        # 1. STRONG SMOOTHING (Moving Average)
        # We average 5 samples to kill the jitter
        self.raw_buffer = collections.deque(maxlen=5)
        
        # 2. ROLLING BASELINE (DC Offset)
        # We track the average over 50 samples (approx 2.5s) to find the "Center Line"
        self.baseline_buffer = collections.deque(maxlen=50)
        
        # 3. STATE MACHINE
        self.last_beat_time = time.time()
        self.beat_detected = False
        
        # 4. BPM SMOOTHING
        # We keep the last 5 valid BPMs to prevent "88 -> 44 -> 88" jumps
        self.bpm_history = collections.deque(maxlen=5)

        start_bpm = 70
        for _ in range(5):
            self.bpm_history.append(start_bpm)
        self.current_bpm = start_bpm
        
        # GSR
        self.gsr_history = collections.deque(maxlen=500)

    def process_pulse(self, raw_val):
        current_time = time.time()
        
        # RE-PROCESS: Smooth the raw input
        self.raw_buffer.append(raw_val)
        if len(self.raw_buffer) < 5: return self.current_bpm
        smoothed = int(statistics.mean(self.raw_buffer))
        
        # TRACK BASELINE: Find the center of the wave
        self.baseline_buffer.append(smoothed)
        if len(self.baseline_buffer) < 20: return self.current_bpm
        
        baseline = statistics.mean(self.baseline_buffer)
        
        # THRESHOLD: We look for the signal crossing ABOVE the baseline
        # We add a small offset (100 units) to avoid triggering on tiny noise
        threshold = baseline + 100 
        
        # DETECTION LOGIC
        # Rising Edge: Signal goes above threshold
        if smoothed > threshold and not self.beat_detected:
            self.beat_detected = True
            
            delta_time = current_time - self.last_beat_time
            self.last_beat_time = current_time
            
            # BPM CALCULATION & FILTER
            # We accept anything between 40 BPM (1.5s) and 200 BPM (0.3s)
            if 0.3 < delta_time < 1.5:
                instant_bpm = 60.0 / delta_time
                self.bpm_history.append(instant_bpm)
                
                # OUTPUT SMOOTHING
                # We return the average of the last few beats
                self.current_bpm = int(statistics.mean(self.bpm_history))
                
                # Optional: Debug Print
                print(f"BEAT! BPM: {self.current_bpm} (Interval: {delta_time:.2f}s)")

        # Falling Edge: Signal drops BELOW the baseline
        # We require it to drop slightly below baseline to reset
        if smoothed < baseline - 50:
            self.beat_detected = False

        return self.current_bpm

    def process_gsr(self, raw_val):
        # 1. Fill the History Buffer
        self.gsr_history.append(raw_val)
        
        # We need a few seconds of data before we can judge stress
        if len(self.gsr_history) < 50:
            return 0
            
        # 2. Find the Dynamic Range (Over last 25 seconds)
        # Note: In most circuits, High Value = Dry (Calm), Low Value = Wet (Stress)
        max_val = max(self.gsr_history) # The Calmest you've been
        min_val = min(self.gsr_history) # The Most Stressed you've been
        
        range_span = max_val - min_val
        
        # Avoid division by zero if flatline
        if range_span < 10:
            return 0
            
        # 3. Calculate Relative GSR values (0-100)
        # "How close is the current value to the 'Wet' (Min) limit?"
        # If Current == Min, gsr_processed = 100. If Current == Max, gsr_processed = 0.
        gsr_processed = (max_val - raw_val) / range_span
        
        # Clamp to 0.0 - 1.0
        gsr_processed = max(0.0, min(1.0, gsr_processed))
        
        # Convert to 0-100 integer
        return int(gsr_processed * 100)

def main():
    # Setup UDP Socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Setup the signal processing class
    processor = BioProcessor()

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
                        data = json.loads(raw_line)

                        sock.sendto(raw_line.encode(), (UDP_IP, UDP_PORT))
                        
                        #  Get Raw Data
                        raw_gsr = data.get("gsr", 0)
                        raw_pulse = data.get("pulse", 0)
                        
                        # Process Data
                        final_bpm = processor.process_pulse(raw_pulse)
                        final_gsr = processor.process_gsr(raw_gsr)

                        unity_payload = {
                            "sensor_1": raw_gsr,  # Currently GSR
                            "sensor_2": raw_pulse   # Currently Pulse
                        }

                        # TRANSMIT: Send to Unity
                        message = json.dumps(unity_payload).encode()
                        sock.sendto(message, (UDP_IP, UDP_PORT))
                        
                        print(f"BPM: {final_bpm} (Raw: {raw_pulse}) | GSR (Processed): {final_gsr} (Raw: {raw_gsr})")
                        
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