import soundcard as sc
import numpy as np
from faster_whisper import WhisperModel
import sys
import threading
import queue
import time
from datetime import datetime

# --- Configuration ---
MODEL_SIZE = "small"   
SAMPLE_RATE = 16000
CHUNK_DURATION = 5          # Record in 5-second blocks
MAX_QUEUE_SIZE = 10         # Alert if we are lagging behind by more than 50 seconds

# Thread-safe queue for audio chunks
audio_queue = queue.Queue()

def record_worker():
    """
    Runs in a background thread. Continuously records audio 
    and puts it into the queue.
    """
    try:
        mic = sc.default_microphone()
        # print(f"[Thread] Recording started on {mic.name}...")
        
        while True:
            # Record 5 seconds
            data = mic.record(samplerate=SAMPLE_RATE, numframes=SAMPLE_RATE * CHUNK_DURATION)
            
            # Preprocess to Mono immediately to save RAM
            if data.shape[1] > 1:
                data = data.mean(axis=1)
            else:
                data = data.squeeze()
            
            data = data.flatten().astype(np.float32)
            
            # Put into queue for the AI to process
            audio_queue.put(data)
            
    except Exception as e:
        print(f"❌ Recording Thread Died: {e}")

def main():
    print(f"--- 🧵 Initializing Threaded Translator ({MODEL_SIZE}) ---")
    print(f"--- 💾 Saving log to: meeting_log.txt ---")
    
    # 1. Load Model (Main Thread)
    print(f"Loading Whisper model '{MODEL_SIZE}'...")
    model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
    
    # 2. Start Recorder Thread
    recorder_thread = threading.Thread(target=record_worker, daemon=True)
    recorder_thread.start()
    
    print(f"✅ Ready! Recording in background...")
    print("🔴 Press Ctrl+C to exit.\n")

    log_file = open("meeting_log.txt", "a", encoding="utf-8")

    try:
        while True:
            # 3. Get Audio from Queue
            # This blocks until data is available
            audio_data = audio_queue.get()
            
            # Check for lag
            q_size = audio_queue.qsize()
            if q_size > 1:
                print(f"⚠️  Lag Warning: {q_size} chunks queued ({q_size * CHUNK_DURATION}s behind)")

            # --- PASS 1: Transcribe (Japanese) ---
            segments_ja, _ = model.transcribe(
                audio_data, 
                beam_size=5, 
                task="transcribe", 
                vad_filter=True,
                condition_on_previous_text=False,
                repetition_penalty=1.2
            )
            text_ja = " ".join([s.text for s in segments_ja]).strip()

            if text_ja:
                # --- PASS 2: Translate (English) ---
                segments_en, _ = model.transcribe(
                    audio_data, 
                    beam_size=5, 
                    task="translate", 
                    vad_filter=True,
                    condition_on_previous_text=False,
                    repetition_penalty=1.2
                )
                text_en = " ".join([s.text for s in segments_en]).strip()

                # --- Output & Log ---
                timestamp = datetime.now().strftime("%H:%M:%S")
                
                # Console
                sys.stdout.write("\033[K")
                print(f"[{timestamp}] 🇯🇵 {text_ja}")
                print(f"           🇺🇸 {text_en}")
                print("-" * 40)
                
                # File
                log_file.write(f"[{timestamp}]\nJA: {text_ja}\nEN: {text_en}\n\n")
                log_file.flush()

    except KeyboardInterrupt:
        print("\n\n🛑 User stopped execution.")
    except Exception as e:
        print(f"\n❌ Error: {e}")
    finally:
        log_file.close()

if __name__ == "__main__":
    main()
