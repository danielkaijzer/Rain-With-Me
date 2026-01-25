import os
import time
import json
import socket
import pyaudio
import wave
from google import genai
from google.genai import types
from dotenv import load_dotenv

# --- CONFIGURATION ---
load_dotenv()
api_key = os.getenv('MY_API_KEY')
os.environ["GOOGLE_API_KEY"] = str(api_key)

if api_key:
    print("API Key loaded successfully!")
else:
    print("API Key not found. Check your .env file.")

# Audio Settings
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
RECORD_SECONDS = 3 

# Unity Connection
UDP_IP = "127.0.0.1"
UDP_PORT = 5006

# --- SETUP GEMINI (NEW SDK) ---
client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])

def record_audio_chunk(filename):
    """Records a short audio clip from the microphone."""
    p = pyaudio.PyAudio()
    
    if p.get_device_count() == 0:
        print("❌ No Microphone Found!")
        return

    print("🎤 Listening...", end="\r")
    
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)

    frames = []

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

def main():
    print(f"📡 Voice Sentiment Engine Active (Google GenAI v2)")
    print(f"🌊 Sending to Unity on {UDP_IP}:{UDP_PORT}")
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    temp_file = "temp_voice.wav"

    try:
        while True:
            # 1. Record
            record_audio_chunk(temp_file)
            
            # 2. Analyze
            try:
                print("🧠 Analyzing...   ", end="\r")
                
                # --- FIX IS HERE: Use 'file=' instead of 'path=' ---
                audio_file = client.files.upload(file=temp_file)
                
                # B. Generate Content
                response = client.models.generate_content(
                    model='gemini-2.0-flash', # Using 2.0 Flash for speed
                    contents=[
                        audio_file,
                        "Analyze the tone and sentiment of this audio."
                    ],
                    config=types.GenerateContentConfig(
                        system_instruction="""
                        You are a real-time sentiment analysis engine.
                        Return ONLY a JSON object with this structure:
                        {
                            "sentiment": float,  // -1.0 (Negative) to 1.0 (Positive)
                            "arousal": float,    // 0.0 (Calm) to 1.0 (Excited)
                            "summary": string    // 3-word summary
                        }
                        Do not use Markdown.
                        """,
                        response_mime_type="application/json"
                    )
                )
                
                # C. Parse
                clean_text = response.text.strip()
                data = json.loads(clean_text)
                
                sentiment = data.get("sentiment", 0.0)
                arousal = data.get("arousal", 0.0)
                summary = data.get("summary", "...")
                
                print(f"💬 Sentiment: {sentiment:.2f} | 🔥 Arousal: {arousal:.2f} | 📝 {summary}")
                
                # D. Send to Unity
                packet = {
                    "voice_sentiment": sentiment,
                    "voice_arousal": arousal
                }
                sock.sendto(json.dumps(packet).encode(), (UDP_IP, UDP_PORT))
                
                # E. Cleanup (Delete file from Gemini Cloud to save quota)
                # Note: 'audio_file.name' contains the cloud resource ID
                # client.files.delete(name=audio_file.name) 

            except Exception as e:
                print(f"\n⚠️ API Error: {e}")

    except KeyboardInterrupt:
        print("\n👋 Stopping Voice Engine...")
        if os.path.exists(temp_file):
            os.remove(temp_file)

if __name__ == "__main__":
    main()