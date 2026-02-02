import soundcard as sc

def list_audio_devices():
    print("=== 🎤 Microphones (Input) ===")
    try:
        mics = sc.all_microphones(include_loopback=True)
        for i, mic in enumerate(mics):
            print(f"[{i}] {mic.name}")
            # print(f"    ID: {mic.id}") # ID structure varies by backend
    except Exception as e:
        print(f"Error listing microphones: {e}")

    print("\n=== 🎧 Speakers/Monitors (Output) ===")
    try:
        speakers = sc.all_speakers()
        for i, spk in enumerate(speakers):
            print(f"[{i}] {spk.name}")
    except Exception as e:
        print(f"Error listing speakers: {e}")

if __name__ == "__main__":
    list_audio_devices()
