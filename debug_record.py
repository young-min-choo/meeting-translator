import soundcard as sc
import soundfile as sf
import numpy as np
import time

def debug_record():
    print("Listing devices...")
    mics = sc.all_microphones(include_loopback=True)
    for i, m in enumerate(mics):
        print(f"[{i}] {m.name}")
    
    idx = int(input("
Enter device index to record from (usually RDPSource): "))
    selected_mic = mics[idx]
    
    fs = 16000
    duration = 5 # seconds
    print(f"Recording {duration} seconds from {selected_mic.name}...")
    
    data = selected_mic.record(samplerate=fs, numframes=fs*duration)
    
    # Mono mix
    if data.shape[1] > 1:
        data = data.mean(axis=1)
    
    filename = "debug_capture.wav"
    sf.write(filename, data, fs)
    print(f"Saved to {filename}")
    print("Transfer this file to Windows and play it. If it sounds distorted, we have a sample rate issue.")

if __name__ == "__main__":
    debug_record()
