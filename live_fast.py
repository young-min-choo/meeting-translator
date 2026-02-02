import soundcard as sc
import numpy as np
from faster_whisper import WhisperModel
import sys
import threading
import queue
import time
from datetime import datetime

# --- Configuration for Speed ---
# "base" is ~2x faster than "small", but still better than "tiny"
MODEL_SIZE = "base"   
SAMPLE_RATE = 16000
CHUNK_DURATION = 5          
MAX_QUEUE_SIZE = 10         

# Thread-safe queue
audio_queue = queue.Queue()

def record_worker():
    """Continuous recording thread"""
    try:
        mic = sc.default_microphone()
        while True:
            data = mic.record(samplerate=SAMPLE_RATE, numframes=SAMPLE_RATE * CHUNK_DURATION)
            if data.shape[1] > 1:
                data = data.mean(axis=1)
            else:
                data = data.squeeze()
            data = data.flatten().astype(np.float32)
            audio_queue.put(data)
    except Exception as e:
        print(f"❌ Recording Thread Died: {e}")

def main():
    print(f"--- ⚡ Initializing FAST Mode ({MODEL_SIZE}) ---")
    print(f"--- 🏎️ Optimizations: Beam Size=1, Model=Base ---")
    
    print(f"Loading Whisper model '{MODEL_SIZE}'...")
    model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
    
    recorder_thread = threading.Thread(target=record_worker, daemon=True)
    recorder_thread.start()
    
    print(f"✅ Ready! Recording...")
    print("🔴 Press Ctrl+C to exit.\n")

    log_file = open("meeting_log_fast.txt", "a", encoding="utf-8")

    try:
        while True:
            audio_data = audio_queue.get() 
            
            # Monitor Lag
            q_size = audio_queue.qsize()
            if q_size > 0:
                print(f"⚠️  Lag: {q_size} chunks")

            # --- PASS 1: Transcribe (Japanese) ---
            # BEAM_SIZE=1 is the key speedup here. 
            # It stops the model from checking 5 alternative sentence possibilities.
            segments_ja, _ = model.transcribe(
                audio_data, 
                beam_size=1, 
                task="transcribe", 
                vad_filter=True,
                condition_on_previous_text=False
            )
            text_ja = " ".join([s.text for s in segments_ja]).strip()

            if text_ja:
                # --- PASS 2: Translate (English) ---
                segments_en, _ = model.transcribe(
                    audio_data, 
                    beam_size=1, 
                    task="translate", 
                    vad_filter=True,
                    condition_on_previous_text=False
                )
                text_en = " ".join([s.text for s in segments_en]).strip()

                timestamp = datetime.now().strftime("%H:%M:%S")
                
                sys.stdout.write("\033[K")
                print(f"[{timestamp}] 🇯🇵 {text_ja}")
                print(f"           🇺🇸 {text_en}")
                print("-" * 40)
                
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
