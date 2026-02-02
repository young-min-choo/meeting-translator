import soundcard as sc
import numpy as np
from faster_whisper import WhisperModel
import sys

# Configuration
MODEL_SIZE = "small"    # Upgraded to 'small' for better translation quality (vs 'tiny')
SAMPLE_RATE = 16000
CHUNK_DURATION = 5

def main():
    print(f"--- 🌐 Initializing Live Translator ({MODEL_SIZE}) ---")
    print(f"--- 🎯 Target: English Output ---")
    
    # Load Model
    print(f"Loading Whisper model... (This might take a moment)")
    model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
    
    # Get Mic
    mic = sc.default_microphone()
    print(f"✅ Ready! Listening on device: {mic.name}")
    print("📝 format: [Listening...] -> [Translating to English...] -> [Output]")
    print("🔴 Press Ctrl+C to exit.\n")

    try:
        while True:
            # 1. Record
            print("🎤 Listening...", end="\r")
            data = mic.record(samplerate=SAMPLE_RATE, numframes=SAMPLE_RATE * CHUNK_DURATION)
            
            # 2. Preprocess (Stereo -> Mono)
            if data.shape[1] > 1:
                data = data.mean(axis=1)
            else:
                data = data.squeeze()

            # 3. Translate
            data = data.flatten().astype(np.float32)
            
            # task="translate" tells Whisper to output English text, 
            # regardless of the input language (Japanese, etc.)
            segments, info = model.transcribe(data, beam_size=5, task="translate")

            # 4. Output
            output_buffer = []
            for segment in segments:
                if segment.text.strip():
                    output_buffer.append(segment.text)
            
            if output_buffer:
                sys.stdout.write("\033[K") 
                # Print info about detected source language
                lang_code = info.language.upper()
                print(f"[{lang_code} -> EN] {' '.join(output_buffer)}")
            else:
                pass

    except KeyboardInterrupt:
        print("\n\n🛑 User stopped execution.")
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    main()
