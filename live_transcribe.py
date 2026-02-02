import soundcard as sc
import numpy as np
from faster_whisper import WhisperModel
import sys

# Configuration
MODEL_SIZE = "tiny"     # "tiny", "base", "small", "medium", "large"
SAMPLE_RATE = 16000     # Whisper expects 16kHz
CHUNK_DURATION = 5      # Record in 5-second blocks

def main():
    print(f"--- 🚀 Initializing Live Transcriber ({MODEL_SIZE}) ---")
    
    # Load Model
    print(f"Loading Whisper model... (This might take a moment)")
    # Using 'int8' for CPU efficiency. 
    model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
    
    # Get Mic
    mic = sc.default_microphone()
    print(f"✅ Ready! Listening on device: {mic.name}")
    print("📝 format: [Listening...] -> [Transcribing...] -> [Output]")
    print("🔴 Press Ctrl+C to exit.\n")

    try:
        while True:
            # 1. Record
            print("🎤 Listening...", end="\r")
            data = mic.record(samplerate=SAMPLE_RATE, numframes=SAMPLE_RATE * CHUNK_DURATION)
            
            # 2. Preprocess (Stereo -> Mono)
            # data shape is (frames, channels). We need (frames,)
            if data.shape[1] > 1:
                data = data.mean(axis=1) # Average to mono
            else:
                data = data.squeeze()

            # 3. Transcribe
            # flatten() ensures it's a 1D array
            data = data.flatten().astype(np.float32)
            
            segments, info = model.transcribe(data, beam_size=5, language=None) # Auto-detect language

            # 4. Output
            output_buffer = []
            for segment in segments:
                if segment.text.strip():
                    output_buffer.append(segment.text)
            
            if output_buffer:
                # Clear the "Listening..." line
                sys.stdout.write("\033[K") 
                print(f"🗣️  {' '.join(output_buffer)}")
            else:
                # Optional: Indicate silence or just loop back
                pass

    except KeyboardInterrupt:
        print("\n\n🛑 User stopped execution.")
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    main()
