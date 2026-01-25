import os
import time
import json
import socket
import pyaudio
import wave
import cv2
from google import genai
from google.genai import types
from dotenv import load_dotenv

# --- CONFIGURATION ---
load_dotenv()
api_key = os.getenv('MY_API_KEY')
os.environ["GOOGLE_API_KEY"] = str(api_key)

# Audio Settings
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
RECORD_SECONDS = 3 

# Unity Connection
UDP_IP = "127.0.0.1"
UDP_PORT = 5006

# --- SETUP GEMINI ---
client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])

def find_working_camera():
    """Iterates through indices to find a camera that actually returns a frame."""
    print("Searching for a working webcam...")
    for index in range(5): # Check indices 0 to 4
        cap = cv2.VideoCapture(index)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret and frame is not None and frame.size > 0:
                print(f"Found working camera at Index {index}")
                return cap
            cap.release()
    print("No working webcam found!")
    return None

# --- INITIALIZE WEBCAM ---
cap = find_working_camera()

def record_audio_chunk(filename):
    """Records a short audio clip from the microphone."""
    p = pyaudio.PyAudio()
    
    # Safety check for microphone
    if p.get_device_count() == 0:
        print("No microphone found.")
        return

    stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
    frames = []

    # Record for RECORD_SECONDS
    for _ in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
        data = stream.read(CHUNK, exception_on_overflow=False)
        frames.append(data)

    stream.stop_stream()
    stream.close()
    p.terminate()

    wf = wave.open(filename, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()

def capture_frame(filename):
    """Captures a single frame from the webcam."""
    if cap is None or not cap.isOpened():
        return False
    
    ret, frame = cap.read()
    if ret:
        cv2.imwrite(filename, frame)
        return True
    return False

def main():
    if cap is None:
        print("Exiting: Camera initialization failed.")
        return

    print(f"Multimodal Sentiment Engine Active (Audio + Video)")
    print(f"Sending to Unity on {UDP_IP}:{UDP_PORT}")
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    temp_audio = "temp_voice.wav"
    temp_image = "temp_face.jpg"

    try:
        while True:
            # 1. Capture Data
            print("Recording & Watching...", end="\r")
            
            # A. Record Audio
            record_audio_chunk(temp_audio)
            
            # B. Snap Photo
            has_image = capture_frame(temp_image)

            # Debug: Check if we actually got an image file
            if has_image:
                file_size = os.path.getsize(temp_image)
                if file_size < 1000: # If image is suspiciously small (<1KB)
                    print(f"⚠️ Warning: Captured image is tiny ({file_size} bytes). Camera might be black.")

            # 2. Analyze
            try:
                print("Analyzing...           ", end="\r")
                
                # Upload files
                uploaded_audio = client.files.upload(file=temp_audio)
                input_items = [uploaded_audio]

                if has_image:
                    uploaded_image = client.files.upload(file=temp_image)
                    input_items.append(uploaded_image)

                prompt_text = "Analyze the facial expression in the image and the vocal tone in the audio."

                # Generate Content
                response = client.models.generate_content(
                    model='gemini-2.0-flash',
                    contents=[*input_items, prompt_text],
                    config=types.GenerateContentConfig(
                        system_instruction="""
                        You are an advanced multimodal sentiment engine.
                        Analyze the user's face and voice to determine their emotional state.
                        
                        PRIORITY RULES:
                        1. VISUAL AUTHORITY: If the audio is silent, neutral, or contains no speech, IGNORE the audio and rely 100% on the facial expression.
                        2. AUDIO AUTHORITY: If the face is not visible or unclear, rely 100% on the voice.
                        3. COMBINED: If both are clear, synthesize them.
                        4. ROBUSTNESS: Never return an error. If unsure, output a Neutral (0.5) state.
                        
                        Return ONLY a JSON object:
                        {
                            "sentiment": float,    // 0.0 (Negative) to 1.0 (Positive), 0.5 is Neutral
                            "arousal": float,      // 0.0 (Calm) to 1.0 (Excited/Intense)
                            "dominant_emotion": string, // e.g., "Joy", "Anger", "Neutral", "Boredom"
                            "summary": string      // 5-word observation
                        }
                        """,
                        response_mime_type="application/json"
                    )
                )
                
                # C. Parse (with Safety Net)
                clean_text = response.text.strip()
                
                try:
                    data = json.loads(clean_text)
                except json.JSONDecodeError:
                    print(f"\nJSON Parse Error. Raw: {clean_text}")
                    data = {"sentiment": 0.5, "arousal": 0.0, "dominant_emotion": "Error", "summary": "Parse Fail"}
                
                sentiment = data.get("sentiment", 0.5)
                arousal = data.get("arousal", 0.0)
                emotion = data.get("dominant_emotion", "Neutral")
                summary = data.get("summary", "...")
                
                print(f"Sent: {sentiment:.2f} | Arous: {arousal:.2f} | {emotion}")
                
                # D. Send to Unity
                packet = {
                    "sentiment": sentiment,
                    "arousal": arousal,
                    "emotion": emotion
                }
                sock.sendto(json.dumps(packet).encode(), (UDP_IP, UDP_PORT))
                
                # E. Cleanup (Delete Cloud Files)
                # Note: 'audio_file.name' contains the cloud resource ID
                # client.files.delete(name=uploaded_audio.name) 
                # if has_image: client.files.delete(name=uploaded_image.name)
                
            except Exception as e:
                print(f"\nAPI Error: {e}")

    except KeyboardInterrupt:
        print("\nStopping Engine...")
        if cap: cap.release()
        if os.path.exists(temp_audio): os.remove(temp_audio)
        if os.path.exists(temp_image): os.remove(temp_image)

if __name__ == "__main__":
    main()