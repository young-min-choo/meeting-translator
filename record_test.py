import soundcard as sc
import soundfile as sf
import time

OUTPUT_FILE = "test_recording.wav"
DURATION_SEC = 5
SAMPLE_RATE = 48000

def record_audio():
    print(f"Searching for default microphone...")
    try:
        # Get the default microphone
        mic = sc.default_microphone()
        print(f"Using Microphone: {mic.name}")
        
        print(f"\n🔴 Recording for {DURATION_SEC} seconds... Speak now!")
        
        # Record audio
        # data is a numpy array of shape (frames, channels)
        data = mic.record(samplerate=SAMPLE_RATE, numframes=SAMPLE_RATE * DURATION_SEC)
        
        print("⏹️ Recording stopped.")
        
        # Save to file
        print(f"Saving to {OUTPUT_FILE}...")
        sf.write(file=OUTPUT_FILE, data=data, samplerate=SAMPLE_RATE)
        print("✅ Done!")
        
    except Exception as e:
        print(f"❌ Error during recording: {e}")

if __name__ == "__main__":
    record_audio()
