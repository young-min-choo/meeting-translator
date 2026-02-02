import tkinter as tk
from tkinter import font
import soundcard as sc
import soundfile as sf
import numpy as np
import threading
import queue
import os
import sys
import time
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv

# --- Configuration ---
CHUNK_DURATION = 5
SAMPLE_RATE = 16000
TEMP_FILENAME = "temp_gui.wav"

# Load Env
load_dotenv()

class SubtitleOverlay:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Meeting Translator HUD")
        
        # Window Setup
        self.root.attributes('-topmost', True) # Always on top
        # Removed '-type dock' as it can cause focus issues on some Linux WMs
        self.root.overrideredirect(True)       # Frameless
        
        # Dimensions & Position
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        window_width = 800
        window_height = 120
        x_pos = (screen_width - window_width) // 2
        y_pos = screen_height - window_height - 100 
        
        self.root.geometry(f"{window_width}x{window_height}+{x_pos}+{y_pos}")
        
        # Styling
        self.root.configure(bg='black')
        self.root.attributes('-alpha', 0.8) 
        
        # Text Label
        self.text_label = tk.Label(
            self.root, 
            text="Initializing...", 
            font=("Arial", 20, "bold"),
            fg="#00FF00",
            bg="black",
            wraplength=780,
            justify="center"
        )
        self.text_label.pack(expand=True, fill='both', padx=10, pady=10)
        
        # Instructions Label
        self.status_label = tk.Label(
            self.root,
            text="Right-click to Exit | Listening...",
            font=("Arial", 8),
            fg="gray",
            bg="black"
        )
        self.status_label.pack(side="bottom", pady=5)

        # Bind events to ALL widgets so clicking text doesn't ignore the command
        for widget in [self.root, self.text_label, self.status_label]:
            widget.bind("<Button-3>", self.quit_app)  # Right Click
            widget.bind("<Button-1>", self.start_move) # Left Click Drag
            widget.bind("<B1-Motion>", self.do_move)

        # Logic Setup
        self.audio_queue = queue.Queue()
        self.is_running = True
        self.client = None
        
        # Initialize Client
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            self.text_label.config(text="❌ Error: OPENAI_API_KEY missing.\nCheck .env file.")
        else:
            self.client = OpenAI(api_key=api_key)
            self.text_label.config(text="Waiting for audio...")
            
            # Start Threads
            threading.Thread(target=self.record_worker, daemon=True).start()
            threading.Thread(target=self.process_worker, daemon=True).start()
            
        # Periodic "Keep on Top" enforcement for Linux
        self.enforce_topmost()

    def enforce_topmost(self):
        """Force window to top periodically"""
        if self.is_running:
            self.root.lift()
            self.root.attributes('-topmost', True)
            self.root.after(2000, self.enforce_topmost)

    def start_move(self, event):
        self.x = event.x
        self.y = event.y

    def do_move(self, event):
        deltax = event.x - self.x
        deltay = event.y - self.y
        x = self.root.winfo_x() + deltax
        y = self.root.winfo_y() + deltay
        self.root.geometry(f"+{x}+{y}")

    def quit_app(self, event=None):
        print("Exiting...")
        self.is_running = False
        self.root.quit()

    def update_text_safe(self, text, is_status=False):
        """Thread-safe UI update"""
        if is_status:
            self.root.after(0, lambda: self.status_label.config(text=text))
        else:
            self.root.after(0, lambda: self.text_label.config(text=text))

    def record_worker(self):
        try:
            mic = sc.default_microphone()
            while self.is_running:
                data = mic.record(samplerate=SAMPLE_RATE, numframes=SAMPLE_RATE * CHUNK_DURATION)
                if data.shape[1] > 1:
                    data = data.mean(axis=1)
                else:
                    data = data.squeeze()
                self.audio_queue.put(data)
        except Exception as e:
            print(f"Rec Error: {e}")

    def process_worker(self):
        while self.is_running:
            try:
                data = self.audio_queue.get()
                
                # Check for lag
                q_size = self.audio_queue.qsize()
                status_text = "Listening..."
                if q_size > 1:
                    status_text = f"Listening... (Lag: {q_size * CHUNK_DURATION}s)"
                
                # --- SILENCE FILTER (RMS Energy Check) ---
                rms = np.sqrt(np.mean(data**2))
                SILENCE_THRESHOLD = 0.01  # Adjust if it cuts off quiet voices
                
                if rms < SILENCE_THRESHOLD:
                    print(f"DEBUG: Silence detected (RMS: {rms:.4f}) - Skipping API")
                    self.update_text_safe(f"Right-click to Exit | {status_text} (Silence)", is_status=True)
                    continue
                # -----------------------------------------

                self.update_text_safe(f"Right-click to Exit | {status_text} (Processing)", is_status=True)

                sf.write(TEMP_FILENAME, data, SAMPLE_RATE)
                
                if self.client:
                    with open(TEMP_FILENAME, "rb") as audio_file:
                        transcript = self.client.audio.translations.create(
                            model="whisper-1", 
                            file=audio_file, 
                            response_format="text"
                        )
                    
                    text = transcript.strip()
                    print(f"DEBUG API Response: {text}") 
                    
                    if len(text) > 2:
                        self.update_text_safe(text)
                        
            except Exception as e:
                print(f"API Error: {e}")
                self.update_text_safe("⚠️ Connection Error")

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = SubtitleOverlay()
    app.run()
