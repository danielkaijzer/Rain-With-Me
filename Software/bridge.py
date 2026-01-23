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
        # SMOOTHING BUFFER
        # self.smoothing_window = collections.deque(maxlen=15)

        # PULSE SETTINGS
        self.pulse_window = collections.deque(maxlen=200) # Smooth the raw signal
        self.last_beat_time = time.time()
        self.bpm_history = collections.deque(maxlen=10)   # Smooth the final BPM
        self.current_bpm = 0
        self.threshold = 0                               # Dynamic threshold
        self.beat_detected = False

        # GSR SETTINGS
        self.gsr_baseline = collections.deque(maxlen=100) # Slow baseline (approx 10s at 10Hz)
        self.gsr_phasic = 0 # The immediate "Stress Spike"


    def process_pulse(self, raw_val):
        current_time = time.time()
        self.pulse_window.append(raw_val)
        
        # We need at least 2 seconds of data to find the "Wave Height"
        if len(self.pulse_window) < 40:
            return self.current_bpm

        # 1. FIND THE SIGNAL RANGE (Dynamic Amplitude)
        # We look at the last 3 seconds to find the highest peak and lowest valley
        local_min = min(self.pulse_window)
        local_max = max(self.pulse_window)
        amplitude = local_max - local_min

        # 2. SET ADAPTIVE THRESHOLD
        # We trigger a beat when the signal crosses 70% of the wave height
        # Example: Low=7000, High=10000 -> Threshold = 9100
        threshold = local_min + (amplitude * 0.7)

        # 3. PEAK DETECTION
        # Rule A: Signal is above the 70% mark
        # Rule B: We haven't already counted this beat (beat_detected is False)
        # Rule C: The wave is actually big enough (>300 units) to be a heartbeat, not noise
        if raw_val > threshold and not self.beat_detected and amplitude > 300:
            self.beat_detected = True
            
            # Measure time since last beat
            delta_time = current_time - self.last_beat_time
            self.last_beat_time = current_time
            
            # Filter: 40 BPM (1.5s) to 180 BPM (0.33s)
            if 0.33 < delta_time < 1.5:
                instant_bpm = 60.0 / delta_time
                self.bpm_history.append(instant_bpm)
                
                # Smooth the output (Average of last 5 valid beats)
                self.current_bpm = int(statistics.mean(self.bpm_history))
                print(f"BEAT! BPM: {self.current_bpm} (Amp: {amplitude})")

        # 4. RESET
        # We only reset the trigger when the signal drops below 50%
        # This prevents "Double Counting" on the jittery peak
        reset_threshold = local_min + (amplitude * 0.5)
        if raw_val < reset_threshold:
            self.beat_detected = False

        return self.current_bpm


    # def process_pulse(self, raw_val):
    #     """
    #     Converts Raw PPG Waveform -> BPM
    #     Uses a simple dynamic threshold peak detector.
    #     """
    #     current_time = time.time()
        
    #     # 1. Smooth the noise
    #     self.pulse_window.append(raw_val)

    #     if len(self.pulse_window) < 50:
    #         return 0
        
    #     # Calculate the 'DC Offset' (The average line)
    #     baseline = statistics.mean(self.pulse_window)

    #     # Peak Detection Logic
    #     # If signal goes ABOVE threshold and we haven't seen a beat recently...
    #     if raw_val > self.threshold and not self.beat_detected:
    #         # We found a peak!
    #         self.beat_detected = True
            
    #         # Calculate time difference
    #         delta_time = current_time - self.last_beat_time
    #         self.last_beat_time = current_time
            
    #         # Filter Logic: 40-200 BPM is valid
    #         if 0.3 < delta_time < 1.5:
    #             instant_bpm = 60.0 / delta_time
    #             self.bpm_history.append(instant_bpm)
    #             self.current_bpm = int(statistics.mean(self.bpm_history))

    #     # Reset beat detection when signal falls back down
    #     if raw_val < baseline:
    #         self.beat_detected = False

    #     return self.current_bpm

    def process_gsr(self, raw_val):
        """
        Converts Absolute Resistance -> Relative Stress Score
        """
        # 1. Update Baseline (Slowly)
        self.gsr_baseline.append(raw_val)
        baseline = statistics.mean(self.gsr_baseline)
        
        # 2. Calculate Phasic Change (The Spike)
        # For most GSR sensors: Lower Value = More Conductive = More Stress
        # So: (High Baseline) - (Low Current) = Positive Stress Score
        phasic_change = baseline - raw_val
        
        # 3. Simple Noise Gate
        if abs(phasic_change) < 5: 
            phasic_change = 0
            
        return int(phasic_change)

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
                        stress_score = processor.process_gsr(raw_gsr)

                        unity_payload = {
                            "sensor_1": raw_gsr,  # Currently GSR
                            "sensor_2": raw_pulse   # Currently Pulse
                        }

                        # TRANSMIT: Send to Unity
                        message = json.dumps(unity_payload).encode()
                        sock.sendto(message, (UDP_IP, UDP_PORT))
                        
                        print(f"BPM: {final_bpm} (Raw: {raw_pulse}) | Stress: {stress_score} (Raw: {raw_gsr})")
                        
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