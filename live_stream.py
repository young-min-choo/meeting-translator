import os
import sys
import threading
import queue
import time
import soundcard as sc
import numpy as np
from dotenv import load_dotenv
from deepgram import DeepgramClient
from openai import OpenAI
from concurrent.futures import ThreadPoolExecutor

# Load environment variables
load_dotenv()

# Constants
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SAMPLE_RATE = 16000
CHANNELS = 1

# Colors
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RESET = "\033[0m"

if not DEEPGRAM_API_KEY:
    print("❌ Error: DEEPGRAM_API_KEY not found in .env")
    sys.exit(1)

# Initialize OpenAI for Translation
openai_client = None
if OPENAI_API_KEY:
    openai_client = OpenAI(api_key=OPENAI_API_KEY)
else:
    print("⚠️  Warning: OPENAI_API_KEY not found. Translation will be disabled.")

# Executor for non-blocking translation
executor = ThreadPoolExecutor(max_workers=3)

def select_audio_device():
    """Lists available devices and asks user to select one"""
    print("\n🔍 Scanning Audio Devices...")
    mics = sc.all_microphones(include_loopback=True)
    
    print(f"\n{CYAN}=== Available Inputs ==={RESET}")
    default_mic = sc.default_microphone()
    
    for i, mic in enumerate(mics):
        marker = " "
        if mic.name == default_mic.name:
            marker = "*"
        print(f"[{i}] {marker} {mic.name}")
    
    print(f"\n{YELLOW}Tip: For Zoom/Meets, choose a 'Monitor' or 'Loopback' device.{RESET}")
    print(f"{YELLOW}Tip: For In-Person, choose your physical Microphone (*).{RESET}")
    
    try:
        selection = input(f"\nSelect Device Index [Default={default_mic.name}]: ").strip()
        if not selection:
            return default_mic
        
        index = int(selection)
        if 0 <= index < len(mics):
            print(f"✅ Selected: {mics[index].name}")
            return mics[index]
        else:
            print("❌ Invalid index. Using default.")
            return default_mic
    except Exception:
        print("❌ Invalid input. Using default.")
        return default_mic

def translate_and_print(sentence, speaker, color):
    """Translates text and prints the result"""
    try:
        translated_text = sentence # Default to original
        
        if openai_client:
            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a simultaneous interpreter. Translate the following Japanese text to English concisely. Output ONLY the English text."},
                    {"role": "user", "content": sentence}
                ],
                max_tokens=60
            )
            translated_text = response.choices[0].message.content.strip()

        print(f"{color}[{speaker}] 🇯🇵 {sentence}")
        print(f"{color}       ↳ 🇺🇸 {translated_text}{RESET}")
        
    except Exception as e:
        print(f"{color}[{speaker}] 🇯🇵 {sentence} (Translation Failed: {e}){RESET}")

def main():
    try:
        # 0. Select Device
        mic_device = select_audio_device()

        # 1. Setup Deepgram Client
        deepgram = DeepgramClient(api_key=DEEPGRAM_API_KEY)
        
        # 3. Define Event Handlers
        def on_message(result, **kwargs):
            # Check if this is a Results event
            if getattr(result, "type", None) == "Results":
                sentence = result.channel.alternatives[0].transcript
                if len(sentence) == 0:
                    return
                
                # Check for speaker (Diarization)
                speaker = "Unknown"
                if result.channel.alternatives[0].words:
                    # Calculate dominant speaker (majority vote)
                    speaker_counts = {}
                    for word in result.channel.alternatives[0].words:
                        s_id = word.speaker
                        speaker_counts[s_id] = speaker_counts.get(s_id, 0) + 1
                    
                    # Get speaker with max counts
                    dominant_speaker = max(speaker_counts, key=speaker_counts.get)
                    speaker = f"Speaker {dominant_speaker}"

                # Colorize based on speaker
                color = CYAN
                if "0" in speaker: color = GREEN
                elif "1" in speaker: color = YELLOW
                
                # Offload translation to thread pool to keep socket alive
                executor.submit(translate_and_print, sentence, speaker, color)
            
            elif getattr(result, "type", None) == "Metadata":
                pass

        def on_error(error, **kwargs):
            print(f"\n\n❌ Deepgram Error: {error}\n\n")

        # 4. Connect using the V1 Context Manager
        # Note: All boolean/int options must be strings for this SDK version's connect method
        options = {
            "model": "nova-2", 
            "language": "ja", 
            "smart_format": "true", 
            "encoding": "linear16", 
            "channels": "1", 
            "sample_rate": str(SAMPLE_RATE),
            "diarize": "true",
            "interim_results": "false",
        }

        print(f"--- 🚀 Connecting to Deepgram (JP -> Text + Speaker) ---")
        
        # Use the context manager to open the connection
        with deepgram.listen.v1.connect(**options) as dg_connection:
            
            # Register handlers
            dg_connection.on("message", on_message)
            dg_connection.on("error", on_error)

            # Start a thread to listen for responses (since start_listening blocks)
            # Note: SDK v3+ usually uses start() or start_listening(). 
            # Based on inspection, it is start_listening() or just iterate.
            # We'll use a thread to run start() if available, or start_listening().
            # Checking the SDK file again, V1SocketClient has start_listening().
            # However, some examples use start(). Let's try start() first as it's more common in their docs, 
            # but fall back to start_listening if needed. 
            # Actually, looking at the code dump: V1SocketClient ONLY has start_listening().
            
            def receiver():
                try:
                    if hasattr(dg_connection, "start"):
                        dg_connection.start(options) # Some versions take options here
                    elif hasattr(dg_connection, "start_listening"):
                        dg_connection.start_listening()
                except Exception as e:
                    pass # Connection closed
            
            receive_thread = threading.Thread(target=receiver, daemon=True)
            receive_thread.start()

            # 5. Start Audio Stream
            stop_event = threading.Event()

            def audio_sender():
                print(f"🎤 Recording started... (Press Ctrl+C to stop)")
                # mic = sc.default_microphone() <--- REMOVED
                
                # Context manager for recording
                with mic_device.recorder(samplerate=SAMPLE_RATE) as recorder: # <--- CHANGED
                    while not stop_event.is_set():
                        # Read chunk (e.g. 0.1s)
                        data = recorder.record(numframes=int(SAMPLE_RATE * 0.1))
                        
                        # Convert to mono if needed
                        if data.shape[1] > 1:
                            data = data.mean(axis=1)
                        else:
                            data = data.squeeze()
                        
                        # Convert to Int16 bytes (Linear16)
                        audio_int16 = (data * 32767).astype(np.int16).tobytes()
                        
                        # Send to Deepgram
                        dg_connection.send_media(audio_int16)

            audio_thread = threading.Thread(target=audio_sender)
            audio_thread.start()

            # Keep main thread alive until interrupt
            while True:
                time.sleep(1)

    except KeyboardInterrupt:
        print("\n\n🛑 Stopping...")
        stop_event.set()
        # Threads are daemon or will stop when stop_event is set
        print("✅ Done.")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
