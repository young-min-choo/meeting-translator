import soundcard as sc
import numpy as np
import time
import sys

def check_levels():
    print("Looking for RDPSource...")
    try:
        # Get all mics to find the right one
        mics = sc.all_microphones(include_loopback=True)
        mic = None
        for m in mics:
            if "RDPSource" in m.name:
                mic = m
                break
        
        if not mic:
            mic = sc.default_microphone()
            
        print(f"Using: {mic.name}")
        
        with mic.recorder(samplerate=16000) as rec:
            print("Recording levels (Press Ctrl+C to stop)...")
            while True:
                data = rec.record(numframes=1600)
                # Mono mix if stereo
                if data.shape[1] > 1:
                    data = data.mean(axis=1)
                
                rms = np.sqrt(np.mean(data**2))
                level = min(50, int(rms * 200)) # Scale for visibility
                bar = "#" * level
                sys.stdout.write(f"\rLevel: [{bar:<50}] {rms:.4f}")
                sys.stdout.flush()
    except KeyboardInterrupt:
        print("\nStopped.")
    except Exception as e:
        print(f"\nError: {e}")

if __name__ == "__main__":
    check_levels()