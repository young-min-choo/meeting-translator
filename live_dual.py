import soundcard as sc
import numpy as np
from faster_whisper import WhisperModel
import sys

# Configuration
MODEL_SIZE = "small"   
SAMPLE_RATE = 16000
CHUNK_DURATION = 5

def main():
    print(f"--- 🎌 Initializing Dual Mode (Transcribe + Translate) ---")
    print(f"--- 🐢 Note: Running two passes. Latency will be higher. ---")
    
    # Load Model
    print(f"Loading Whisper model '{MODEL_SIZE}'...")
    # vad_filter=True is built-in to faster-whisper. We enable it during transcribe.
    model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
    
    # Get Mic
    mic = sc.default_microphone()
    print(f"✅ Ready! Listening on device: {mic.name}")
    print("🔴 Press Ctrl+C to exit.\n")

    try:
        while True:
            # 1. Record
            print("🎤 Listening...", end="\r")
            data = mic.record(samplerate=SAMPLE_RATE, numframes=SAMPLE_RATE * CHUNK_DURATION)
            
            # 2. Preprocess
            if data.shape[1] > 1:
                data = data.mean(axis=1)
            else:
                data = data.squeeze()
            data = data.flatten().astype(np.float32)

            # --- PASS 1: Transcribe (Get Japanese) ---
            # VAD Filter: Removes silence so we don't hallucinate French/Korean
            # Repetition Penalty: Reduces "jump jump jump"
            segments_ja, _ = model.transcribe(
                data, 
                beam_size=5, 
                task="transcribe", 
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=500),
                condition_on_previous_text=False,
                repetition_penalty=1.2
            )
            
            text_ja = " ".join([s.text for s in segments_ja]).strip()

            # Only proceed to translation if speech was actually detected
            if text_ja:
                # --- PASS 2: Translate (Get English) ---
                segments_en, _ = model.transcribe(
                    data, 
                    beam_size=5, 
                    task="translate", 
                    vad_filter=True,
                    condition_on_previous_text=False,
                    repetition_penalty=1.2
                )
                text_en = " ".join([s.text for s in segments_en]).strip()

                # --- Output Stacked ---
                sys.stdout.write("\033[K") # Clear "Listening..." line
                print(f"🇯🇵 {text_ja}")
                print(f"🇺🇸 {text_en}")
                print("-" * 30)
            else:
                # Silence detected. Just loop back.
                pass

    except KeyboardInterrupt:
        print("\n\n🛑 User stopped execution.")
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    main()
