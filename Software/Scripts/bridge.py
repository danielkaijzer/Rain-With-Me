import os
import time
import json
import socket
import pyaudio
import wave
import cv2
import threading
import collections
import statistics
import serial.tools.list_ports
from google import genai
from google.genai import types
from dotenv import load_dotenv

# --- CONFIGURATION ---
load_dotenv()
api_key = os.getenv('MY_API_KEY')
os.environ["GOOGLE_API_KEY"] = str(api_key)

# Networking
UDP_IP = "127.0.0.1"
UDP_PORT = 5015  

# Audio Settings
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
RECORD_SECONDS = 3 

# Weights
WEIGHT_GSR = 0.6
WEIGHT_GEMINI = 0.4

# --- SHARED GLOBAL STATE ---
# These are read/written by different threads
shared_state = {
    "gsr_arousal": 0.0,
    "bpm": 0,
    "gemini_arousal": 0.5,   # Default neutral
    "gemini_sentiment": 0.0,
    "gemini_emotion": "Waiting...",
    "arduino_connected": False,
    "running": True
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

        # GSR (Updated for Sensitivity)
        self.gsr_baseline_buffer = collections.deque(maxlen=200) 
        
        # CHANGED: Start much lower so small breaths register immediately
        self.max_phasic_peak = 5.0 

    def process_pulse(self, raw_val):
        # (Pulse logic remains the same)
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
        # 1. Add to baseline buffer
        self.gsr_baseline_buffer.append(raw_val)
        if len(self.gsr_baseline_buffer) < 20: return 0.0
        
        # 2. Calculate baseline (Tonic)
        baseline = statistics.mean(self.gsr_baseline_buffer)
        
        # 3. Calculate Phasic (The Drop)
        phasic_diff = baseline - raw_val
        
        if phasic_diff < 0:
            phasic_diff = 0
            
        # 4. Auto-Scaling with Faster Decay
        # CHANGED: Decay faster (0.995) so the bar doesn't get stuck at 100%
        self.max_phasic_peak *= 0.995 
        
        # CHANGED: Never let the max scale drop below 5.0 (Noise Floor)
        if self.max_phasic_peak < 5.0:
            self.max_phasic_peak = 5.0

        # Expand scale if we hit a new high
        if phasic_diff > self.max_phasic_peak:
            self.max_phasic_peak = phasic_diff
            
        # 5. Normalize
        arousal = phasic_diff / self.max_phasic_peak
        
        # OPTIONAL: Un-comment this to see the raw math in your console
        # print(f"Raw: {raw_val} | Base: {baseline:.1f} | Diff: {phasic_diff:.1f} | Peak: {self.max_phasic_peak:.1f}")
        
        return max(0.0, min(1.0, arousal))

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
                        
                        # Process & Update Globals instantly
                        bpm = processor.process_pulse(data.get("pulse", 0))
                        gsr_norm = processor.process_gsr(data.get("gsr", 0))
                        
                        shared_state["bpm"] = bpm
                        shared_state["gsr_arousal"] = gsr_norm
                        
                except Exception:
                    pass
    except Exception as e:
        print(f"⚠️ Arduino Thread Error: {e}")
        shared_state["arduino_connected"] = False

# --- THREAD 2: HIGH-SPEED UDP SENDER ---
def udp_sender_loop():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    print("🚀 High-Speed UDP Sender Active (20Hz)")
    
    while shared_state["running"]:
        # 1. Grab latest values (Thread Safe-ish reading)
        curr_gsr = shared_state["gsr_arousal"]
        curr_ai_arousal = shared_state["gemini_arousal"]
        
        # 2. Calculate Fusion
        if shared_state["arduino_connected"]:
            final_arousal = (curr_gsr * WEIGHT_GSR) + (curr_ai_arousal * WEIGHT_GEMINI)
        else:
            final_arousal = curr_ai_arousal

        # 3. Pack Payload
        packet = {
            "final_arousal": round(final_arousal, 2),
            "gemini_arousal": curr_ai_arousal,
            "gsr_arousal": round(curr_gsr, 2),
            "bpm": shared_state["bpm"],
            "sentiment": shared_state["gemini_sentiment"],
            "emotion": shared_state["gemini_emotion"]
        }

        print(f"GSR: {curr_gsr} | Gemini Arousal: {curr_ai_arousal} | BPM: {shared_state['bpm']} ")
        
        # 4. Send
        try:
            sock.sendto(json.dumps(packet).encode(), (UDP_IP, UDP_PORT))
        except Exception as e:
            print(f"UDP Error: {e}")
            
        # 5. Sleep briefly (20 times per second)
        time.sleep(0.05)

# --- MAIN THREAD: GEMINI LOGIC ---
def main():
    target_port = "/dev/cu.usbmodem12134239842" 
    
    # Start Arduino Thread
    t_arduino = threading.Thread(target=arduino_loop, args=(target_port,), daemon=True)
    t_arduino.start()

    # Start UDP Sender Thread
    t_udp = threading.Thread(target=udp_sender_loop, daemon=True)
    t_udp.start()

    # Setup Gemini
    client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
    
    # Setup Cam
    cap = None
    for i in [0, 1, 2]:
        c = cv2.VideoCapture(i)
        if c.isOpened():
            ret, f = c.read()
            if ret and f.size > 0:
                cap = c
                break
            c.release()
            
    if not cap:
        print("No Webcam Found. Exiting.")
        return

    temp_audio = "fusion_voice.wav"
    temp_image = "fusion_face.jpg"
    
    print(f"🧠 AI Engine Active. Weights -> GSR: {WEIGHT_GSR*100}% | Gemini: {WEIGHT_GEMINI*100}%")

    try:
        while True:
            # --- PHASE 1: COLLECT DATA ---
            # Audio
            p = pyaudio.PyAudio()
            stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
            frames = []
            
            # Record for 3 seconds
            for _ in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
                frames.append(stream.read(CHUNK, exception_on_overflow=False))
            stream.stop_stream()
            stream.close()
            p.terminate()
            
            with wave.open(temp_audio, 'wb') as wf:
                wf.setnchannels(CHANNELS)
                wf.setsampwidth(p.get_sample_size(FORMAT))
                wf.setframerate(RATE)
                wf.writeframes(b''.join(frames))
            
            # Visual (Snapshot) - NO POPUP WINDOW NOW
            ret, frame = cap.read()
            if ret: 
                cv2.imwrite(temp_image, frame)

            # --- PHASE 2: GEMINI INFERENCE ---
            print(f"Analyzing... (Last BPM: {shared_state['bpm']})", end="\r")
            
            try:
                uploaded_audio = client.files.upload(file=temp_audio)
                uploaded_image = client.files.upload(file=temp_image)
                
                response = client.models.generate_content(
                    model='gemini-2.0-flash',
                    contents=[uploaded_audio, uploaded_image, "Analyze face and voice."],
                    config=types.GenerateContentConfig(
                        system_instruction="""
                        Return JSON:
                        {
                            "sentiment": float, // 0.0 (Neg) to 1.0 (Pos)
                            "arousal": float,   // 0.0 (Calm) to 1.0 (High Energy)
                            "emotion": string   // e.g. "Stressed", "Happy"
                        }
                        """,
                        response_mime_type="application/json"
                    )
                )
                data = json.loads(response.text)
                
                # UPDATE SHARED STATE
                # The UDP thread picks this up instantly in its next cycle
                shared_state["gemini_arousal"] = data.get("arousal", 0.5)
                shared_state["gemini_sentiment"] = data.get("sentiment", 0.5)
                shared_state["gemini_emotion"] = data.get("emotion", "Neutral")
                
                print(f"✅ AI Update: {data.get('emotion')} | Arousal: {data.get('arousal')}    ")
                
            except Exception as e:
                print(f"⚠️ Gemini Glitch: {e}")

    except KeyboardInterrupt:
        print("\nStopping...")
        shared_state["running"] = False
        cap.release()
        if os.path.exists(temp_audio): os.remove(temp_audio)
        if os.path.exists(temp_image): os.remove(temp_image)

if __name__ == "__main__":
    main()