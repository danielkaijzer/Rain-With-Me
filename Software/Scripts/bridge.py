import time
import json
import socket
import threading
import collections
import statistics
import serial
import serial.tools.list_ports
from dotenv import load_dotenv

# --- CONFIGURATION ---
# Unity (Where the final data goes)
UNITY_IP = "127.0.0.1"
UNITY_PORT = 5006  

# Internal Link (Where we receive Gemini data from the other script)
GEMINI_LISTENER_PORT = 5015

# Unity Collision Listener Port
UNITY_COLLISION_LISTENER_PORT = 5010

# Distance Sensor Input (Where we listen for the float)
DISTANCE_RX_PORT = 5020
DISTANCE_THRESHOLD = 50.0

# Where Motor Control Data goes
MOTOR_IP = "127.0.0.1"
MOTOR_PORT = 5012

# Weights
WEIGHT_GSR = 0.75
WEIGHT_GEMINI = 0.25

# --- SHARED GLOBAL STATE ---
shared_state = {
    "gsr_arousal": 0.0,
    "bpm": 0,
    "gemini_arousal": 0.5,   # Default neutral
    "gemini_sentiment": 0.0,
    "gemini_emotion": "Waiting for AI...",
    "arduino_connected": False,
    "running": True,
    # Motor state
    "current_distance": 0.0,
    "motor_status": "OFF"
}

# --- CLASS: BIO PROCESSOR ---
class BioProcessor:
    def __init__(self):
        # PULSE
        self.raw_buffer = collections.deque(maxlen=5)
        self.baseline_buffer = collections.deque(maxlen=50)
        self.last_beat_time = time.time()
        self.beat_detected = False
        self.bpm_history = collections.deque(maxlen=5)
        start_bpm = 70
        for _ in range(5): self.bpm_history.append(start_bpm)
        self.current_bpm = start_bpm

        # GSR SETTINGS
        self.gsr_baseline_buffer = collections.deque(maxlen=200) 
        self.min_peak = 15.0      
        self.smooth_factor = 0.1  
        self.max_phasic_peak = self.min_peak
        self.last_arousal_output = 0.0

    def process_pulse(self, raw_val):
        current_time = time.time()
        self.raw_buffer.append(raw_val)
        if len(self.raw_buffer) < 5: return self.current_bpm
        smoothed = int(statistics.mean(self.raw_buffer))
        self.baseline_buffer.append(smoothed)
        if len(self.baseline_buffer) < 20: return self.current_bpm
        baseline = statistics.mean(self.baseline_buffer)
        threshold = baseline + 100 
        if smoothed > threshold and not self.beat_detected:
            self.beat_detected = True
            delta_time = current_time - self.last_beat_time
            self.last_beat_time = current_time
            if 0.3 < delta_time < 1.5:
                instant_bpm = 60.0 / delta_time
                self.bpm_history.append(instant_bpm)
                self.current_bpm = int(statistics.mean(self.bpm_history))
        if smoothed < baseline - 50:
            self.beat_detected = False
        return self.current_bpm

    def process_gsr(self, raw_val):
        # 1. Add to baseline buffer (The "Tonic" level)
        self.gsr_baseline_buffer.append(raw_val)
        if len(self.gsr_baseline_buffer) < 20: return 0.0
        
        baseline = statistics.mean(self.gsr_baseline_buffer)
        
        # 2. Calculate Phasic Drop (The "Spike")
        phasic_diff = baseline - raw_val
        if phasic_diff < 0: phasic_diff = 0
            
        # 3. Auto-Scaling with Limits
        # CHANGE 1: Faster Decay (0.995) so the bar recovers its full range faster
        self.max_phasic_peak *= 0.98
        
        # CHANGE 2: Hard Cap (100.0). Even if you have a massive spike (e.g. 500), 
        # we treat it as 100. This prevents one huge moment from "breaking" the scale.
        if self.max_phasic_peak > 100.0:
            self.max_phasic_peak = 100.0

        # Maintain the floor
        if self.max_phasic_peak < self.min_peak:
            self.max_phasic_peak = self.min_peak

        # Expand if we hit a new high (up to the limit)
        if phasic_diff > self.max_phasic_peak:
            self.max_phasic_peak = phasic_diff
            
        # 4. Normalize
        target_arousal = phasic_diff / self.max_phasic_peak
        target_arousal = max(0.0, min(1.0, target_arousal))
        
        # 5. Smoothing
        self.last_arousal_output += (target_arousal - self.last_arousal_output) * self.smooth_factor
        
        # DEBUG: Un-comment this if you want to see exactly why it's low
        # print(f"DIFF: {phasic_diff:.1f} | CEILING: {self.max_phasic_peak:.1f} | OUT: {self.last_arousal_output:.2f}")

        return round(self.last_arousal_output, 3)

# --- THREAD 1: ARDUINO LISTENER ---
def arduino_loop(serial_port_name):
    print(f"🔌 Connecting to Biosensors on {serial_port_name}...")
    processor = BioProcessor()
    try:
        ser = serial.Serial(serial_port_name, 115200, timeout=1)
        time.sleep(2)
        print("✅ Arduino Connected & Streaming.")
        shared_state["arduino_connected"] = True
        while shared_state["running"]:
            if ser.in_waiting > 0:
                try:
                    line = ser.readline().decode('utf-8').strip()
                    if line.startswith("{") and line.endswith("}"):
                        data = json.loads(line)
                        shared_state["bpm"] = processor.process_pulse(data.get("pulse", 0))
                        shared_state["gsr_arousal"] = processor.process_gsr(data.get("gsr", 0))
                except Exception: pass
    except Exception as e:
        print(f"⚠️ Arduino Thread Error: {e}")
        shared_state["arduino_connected"] = False

# --- THREAD 2: GEMINI LISTENER ---
def gemini_listener_loop():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", GEMINI_LISTENER_PORT))
    sock.settimeout(1.0) # Don't block forever
    print(f"👂 Listening for AI updates on Port {GEMINI_LISTENER_PORT}...")
    
    while shared_state["running"]:
        try:
            data, _ = sock.recvfrom(1024) # Buffer size
            packet = json.loads(data.decode())
            
            # Update the shared state with data from the other script
            shared_state["gemini_arousal"] = packet.get("arousal", 0.5)
            shared_state["gemini_sentiment"] = packet.get("sentiment", 0.5)
            shared_state["gemini_emotion"] = packet.get("emotion", "Neutral")
            
        except socket.timeout:
            continue # Just loop back and check "running"
        except Exception as e:
            print(f"Listener Error: {e}")

# --- THREAD 3: UNITY SENDER (The Hub) ---
def unity_sender_loop():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    print(f"Sending Fusion Data to Unity on {UNITY_PORT} (20Hz)")
    
    while shared_state["running"]:
        curr_gsr = shared_state["gsr_arousal"]
        curr_ai_arousal = shared_state["gemini_arousal"]
        
        # Calculate Fusion
        if shared_state["arduino_connected"]:
            final_arousal = (curr_gsr * WEIGHT_GSR) + (curr_ai_arousal * WEIGHT_GEMINI)
        else:
            final_arousal = curr_ai_arousal

        packet = {
            "final_arousal": round(final_arousal, 2),
            "gemini_arousal": curr_ai_arousal,
            "gsr_arousal": round(curr_gsr, 2),
            "bpm": shared_state["bpm"],
            "sentiment": shared_state["gemini_sentiment"],
            "emotion": shared_state["gemini_emotion"]
        }

        # print(f"FUSION: {final_arousal:.2f} | GSR: {curr_gsr:.2f} | Gemini Arousal: {curr_ai_arousal:.2f} | {shared_state['gemini_emotion']}", end="\r")
        status_msg = (
            f"FUS:{final_arousal:.2f} | "
            f"AI:{shared_state['gemini_emotion']} | "
            f"DIST:{shared_state['current_distance']:.1f} | "
            f"MOT:{shared_state['motor_status']}"
        )
        print(status_msg, end="\r")


        try:
            sock.sendto(json.dumps(packet).encode(), (UNITY_IP, UNITY_PORT))
        except Exception: pass
            
        time.sleep(0.05) # 20Hz update rate

def motor_sender_loop():
    rx_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    rx_sock.bind(("0.0.0.0", DISTANCE_RX_PORT)) # 0.0.0.0 allows listening from external IPs too
    rx_sock.settimeout(0.5)
    
    # 2. Setup Sender Socket (Outgoing Command)
    tx_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    print(f"📏 Listening for Distance on {DISTANCE_RX_PORT} -> Triggering Motor on {MOTOR_PORT}")

    while shared_state["running"]:
        try:
            # Receive Data
            data, _ = rx_sock.recvfrom(1024)
            message = data.decode().strip()
            
            # Parse Float (Handle potential formatting issues)
            try:
                distance_val = float(message)
                shared_state["current_distance"] = distance_val
                
                # Logic: If distance is LESS than threshold, turn ON
                # (You can flip this to > if you want it to trigger when far away)
                if distance_val < DISTANCE_THRESHOLD:
                    command = "1" # Or "on"
                    status = "ON"
                else:
                    command = "0" # Or "off"
                    status = "OFF"
                
                shared_state["motor_status"] = status
                
                # Send Command to Motor Script
                tx_sock.sendto(command.encode(), (MOTOR_IP, MOTOR_PORT))
                
            except ValueError:
                # print(f"Motor Logic: Received non-float data: {message}")
                pass
                
        except socket.timeout:
            continue
        except Exception as e:
            print(f"Motor Loop Error: {e}")


# --- MAIN ---
def main():
    target_port = "/dev/cu.usbmodem12134239842" 
    
    # 1. Start Arduino Thread
    t_arduino = threading.Thread(target=arduino_loop, args=(target_port,), daemon=True)
    t_arduino.start()

    # 2. Start Gemini Listener Thread
    t_listener = threading.Thread(target=gemini_listener_loop, daemon=True)
    t_listener.start()

    # 3. Start Unity Sender Thread
    t_unity_sender = threading.Thread(target=unity_sender_loop, daemon=True)
    t_unity_sender.start()

    # 4. Start Motor Control Sender Thread
    t_motor_sender = threading.Thread(target=motor_sender_loop, daemon=True)
    t_motor_sender.start()

    print("--- FUSION ENGINE RUNNING ---")
    print("Run 'multimodal_sentiment.py' in a separate terminal to enable AI.")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping...")
        shared_state["running"] = False

if __name__ == "__main__":
    main()