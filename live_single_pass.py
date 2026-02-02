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
CHUNK_DURATION = 5          
MAX_QUEUE_SIZE = 10         

# Thread-safe queue
audio_queue = queue.Queue()

# ANSI Colors
GREEN = "\033[92m"
YELLOW = "\033[93m"
GRAY = "\033[90m"
RESET = "\033[0m"

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
    print(f"--- 🎯 Initializing Single-Pass Translator ({MODEL_SIZE}) ---")
    print(f"--- 📉 Optimized: English Only + Confidence Filtering ---")
    
    print(f"Loading Whisper model '{MODEL_SIZE}'...")
    # Use 'small' for decent quality on CPU
    model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
    
    recorder_thread = threading.Thread(target=record_worker, daemon=True)
    recorder_thread.start()
    
    print(f"✅ Ready! Recording...")
    print("🔴 Press Ctrl+C to exit.\n")
    print(f"Key: {GREEN}High Confidence{RESET} | {YELLOW}Unsure{RESET} | {GRAY}Low Confidence{RESET}")

    log_file = open("meeting_log_single.txt", "a", encoding="utf-8")

    try:
        while True:
            audio_data = audio_queue.get()
            
            # Lag Check
            q_size = audio_queue.qsize()
            if q_size > 1:
                print(f"{GRAY}⚠️  Lag: {q_size} chunks{RESET}")

            # --- SINGLE PASS: Translate to English ---
            segments, info = model.transcribe(
                audio_data, 
                beam_size=5, # Better quality than 1, hoping Single Pass makes it fast enough
                task="translate", 
                vad_filter=True,
                condition_on_previous_text=False
            )
            
            # Process segments
            full_text = []
            avg_prob = 0
            count = 0

            for s in segments:
                # Confidence Calculation (exp(logprob) = probability 0.0 to 1.0)
                prob = np.exp(s.avg_logprob)
                
                # Determine Color based on individual segment confidence
                color = GRAY
                suffix = " (?)"
                if prob > 0.8: 
                    color = GREEN
                    suffix = ""
                elif prob > 0.6: 
                    color = YELLOW
                
                text = s.text.strip()
                if text:
                    full_text.append(f"{color}{text}{suffix}{RESET}")
                    
                    # Log to file (clean text only)
                    log_file.write(f"[{datetime.now().strftime('%H:%M:%S')}] ({prob:.2f}) {text}\n")

            if full_text:
                sys.stdout.write("\033[K")
                print(f"🇺🇸 {' '.join(full_text)}")
                log_file.flush()

    except KeyboardInterrupt:
        print("\n\n🛑 User stopped execution.")
    except Exception as e:
        print(f"\n❌ Error: {e}")
    finally:
        log_file.close()

if __name__ == "__main__":
    main()
