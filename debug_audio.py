import soundcard as sc
import numpy as np
import time

SAMPLE_RATE = 16000
DURATION = 5

def debug_audio():
    print("Searching for 'Monitor of RDP Sink'...")
    mics = sc.all_microphones(include_loopback=True)
    target = None
    for m in mics:
        if "Monitor of RDP Sink" in m.name:
            target = m
            break
    
    if not target:
        print("❌ Could not find 'Monitor of RDP Sink'.")
        return

    print(f"✅ Found: {target.name}")
    print(f"🔴 Monitoring volume for {DURATION} seconds... (Play some audio in Zoom now!)")
    
    with target.recorder(samplerate=SAMPLE_RATE) as rec:
        start_time = time.time()
        while time.time() - start_time < DURATION:
            data = rec.record(numframes=int(SAMPLE_RATE * 0.5))
            # Calculate RMS (Volume)
            rms = np.sqrt(np.mean(data**2))
            # Create a simple visual volume bar
            bar = "#" * int(rms * 100)
            print(f"Volume: {rms:.4f} {bar}")

if __name__ == "__main__":
    debug_audio()
