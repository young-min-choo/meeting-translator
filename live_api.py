import soundcard as sc
import soundfile as sf
import numpy as np
import threading
import queue
import time
import os
import sys
from datetime import datetime
from openai import OpenAI

# --- Configuration ---
CHUNK_DURATION = 5          
SAMPLE_RATE = 16000
TEMP_FILENAME = "temp_chunk.wav"

# ANSI Colors
GREEN = "\033[92m"
BLUE = "\033[94m"
RESET = "\033[0m"

# Thread-safe queue
audio_queue = queue.Queue()

def record_worker():
    """Continuous recording thread"""
    try:
        mic = sc.default_microphone()
        while True:
            # Record raw audio
            data = mic.record(samplerate=SAMPLE_RATE, numframes=SAMPLE_RATE * CHUNK_DURATION)
            
            # Mono mix
            if data.shape[1] > 1:
                data = data.mean(axis=1)
            else:
                data = data.squeeze()
                
            audio_queue.put(data)
    except Exception as e:
        print(f"❌ Recording Thread Died: {e}")

def main():
    print(f"--- ☁️  Initializing OpenAI Whisper API Mode ---")
    
    # 1. Setup Client
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ Error: OPENAI_API_KEY environment variable not set.")
        print("Run: export OPENAI_API_KEY='sk-...' then try again.")
        return

    client = OpenAI(api_key=api_key)
    
    # 2. Start Recorder
    recorder_thread = threading.Thread(target=record_worker, daemon=True)
    recorder_thread.start()
    
    print(f"✅ Ready! Recording... (Sending to Cloud)")
    print("🔴 Press Ctrl+C to exit.\n")

    log_file = open("meeting_log_api.txt", "a", encoding="utf-8")

    try:
        while True:
            # Get audio from queue
            data = audio_queue.get()
            
            # Check lag
            q_size = audio_queue.qsize()
            if q_size > 1:
                 print(f"⚠️  Lag: {q_size} chunks queued")

            # Save to temporary file for API upload
            sf.write(TEMP_FILENAME, data, SAMPLE_RATE)
            
            # 3. Call API
            try:
                with open(TEMP_FILENAME, "rb") as audio_file:
                    # We use "translations" endpoint to get direct English output
                    transcript = client.audio.translations.create(
                        model="whisper-1", 
                        file=audio_file,
                        response_format="text" # Simple text response
                    )
                
                text = transcript.strip()
                
                # Filter empty/short hallucinations
                if len(text) > 2:
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    
                    # Print
                    sys.stdout.write("\033[K")
                    print(f"[{timestamp}] 🇺🇸 {GREEN}{text}{RESET}")
                    
                    # Log
                    log_file.write(f"[{timestamp}] {text}\n")
                    log_file.flush()
                
            except Exception as api_err:
                print(f"❌ API Error: {api_err}")

    except KeyboardInterrupt:
        print("\n\n🛑 User stopped execution.")
    except Exception as e:
        print(f"\n❌ Error: {e}")
    finally:
        log_file.close()
        if os.path.exists(TEMP_FILENAME):
            os.remove(TEMP_FILENAME)

if __name__ == "__main__":
    main()
