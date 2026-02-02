from faster_whisper import WhisperModel

model_size = "tiny"
audio_file = "test_recording.wav"

def main():
    print(f"Loading model: {model_size} (CPU)...")
    try:
        # Run on CPU with INT8 for compatibility on most laptops
        # If you have an NVIDIA GPU, change device to "cuda" and compute_type to "float16"
        model = WhisperModel(model_size, device="cpu", compute_type="int8")
        
        print(f"Transcribing {audio_file}...")
        segments, info = model.transcribe(audio_file, beam_size=5)

        print(f"Detected language '{info.language}' with probability {info.language_probability:.2f}")

        print("\n--- Transcription ---")
        for segment in segments:
            print(f"[{segment.start:.2f}s -> {segment.end:.2f}s] {segment.text}")
        print("---------------------")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()

