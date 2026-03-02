import tkinter as tk
from tkinter import simpledialog, scrolledtext
import soundcard as sc
import numpy as np
import threading
import queue
import time
import os
import sys
from dotenv import load_dotenv
from deepgram import DeepgramClient
from deepgram.core.events import EventType
from openai import OpenAI
from concurrent.futures import ThreadPoolExecutor

# Load Env
load_dotenv()

# Constants
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SAMPLE_RATE = 16000
GAIN_BOOST = 5.0  # Increased for Zoom
DEBUG_AUDIO = True

class DeviceSelectionDialog(simpledialog.Dialog):
    def __init__(self, parent):
        try:
            self.devices = sc.all_microphones(include_loopback=True)
        except Exception as e:
            print(f"Error listing devices: {e}")
            self.devices = []
        self.selected_device = None
        super().__init__(parent, title="Select Audio Source")

    def body(self, master):
        tk.Label(master, text="Choose Input Device:", font=("Arial", 12)).pack(pady=10)
        self.listbox = tk.Listbox(master, width=60, height=10, font=("Arial", 10))
        self.listbox.pack(padx=20, pady=10)
        
        try:
            default_mic_name = sc.default_microphone().name
        except:
            default_mic_name = ""
        
        target_idx = 0
        for i, dev in enumerate(self.devices):
            prefix = "  "
            if dev.name == default_mic_name: prefix = "* "
            if "RDPSource" in dev.name:
                prefix = ">> "
                target_idx = i
            self.listbox.insert(tk.END, f"{prefix}{dev.name}")
            
        if self.devices:
            self.listbox.select_set(target_idx)
            self.listbox.see(target_idx)
        return self.listbox

    def apply(self):
        idx = self.listbox.curselection()
        if idx:
            self.selected_device = self.devices[idx[0]]

class TranslatorHUD:
    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw()

        dialog = DeviceSelectionDialog(self.root)
        self.input_device = dialog.selected_device
        
        if not self.input_device:
            sys.exit()

        self.root.deiconify()
        self.root.update_idletasks() # Ensure window is mapped
        self.setup_ui()
        
        self.is_running = True
        self.executor = ThreadPoolExecutor(max_workers=3)
        self.openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
        
        threading.Thread(target=self.start_deepgram, daemon=True).start()

    def setup_ui(self):
        self.root.title("Meeting Translator HUD")
        self.root.attributes('-topmost', True)
        self.root.overrideredirect(True)
        self.root.attributes('-alpha', 0.85)
        self.root.configure(bg='black')

        # Scale based on screen size
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        w = int(sw * 0.8)
        h = int(sh * 0.25)
        
        # Clamp width if it's too large (handling multi-monitor setups)
        if w > 1920: w = 1600 
        
        x = (sw - w) // 2
        y = sh - h - 80 
        
        print(f"DEBUG: Screen Size: {sw}x{sh} | Target Window: {w}x{h} at {x},{y}")
        self.root.geometry(f"{w}x{h}+{x}+{y}")

        self.root.bind("<Button-1>", self.start_move)
        self.root.bind("<B1-Motion>", self.do_move)
        self.root.bind("<Button-3>", self.quit_app)

        self.resize_label = tk.Label(self.root, text="◢", bg="black", fg="gray", font=("Arial", 10))
        self.resize_label.place(relx=1.0, rely=1.0, anchor="se")

        header = tk.Label(self.root, text=f"🔴 Listening: {self.input_device.name} (Gain: {GAIN_BOOST}x)", 
                         bg="black", fg="gray", font=("Arial", 8))
        header.pack(fill="x", pady=2)

        self.text_area = scrolledtext.ScrolledText(self.root, font=("Noto Sans CJK JP", 16), 
                                                  bg="black", fg="white", bd=0, wrap=tk.WORD)
        self.text_area.pack(expand=True, fill="both", padx=15, pady=5)
        
        self.text_area.tag_config("japanese", foreground="#AAAAAA", font=("Noto Sans CJK JP", 12))

    def start_move(self, event):
        self.x, self.y = event.x, event.y
        if event.x > self.root.winfo_width() - 25 and event.y > self.root.winfo_height() - 25:
            self.mode = "resize"
        else:
            self.mode = "move"

    def do_move(self, event):
        if self.mode == "move":
            x = self.root.winfo_x() + (event.x - self.x)
            y = self.root.winfo_y() + (event.y - self.y)
            self.root.geometry(f"+{x}+{y}")
        else:
            self.root.geometry(f"{max(200, event.x)}x{max(100, event.y)}")

    def quit_app(self, event):
        self.is_running = False
        self.root.quit()

    def append_text(self, japanese, english):
        def _update():
            self.text_area.insert(tk.END, f"\n• {english}\n", "white")
            self.text_area.insert(tk.END, f"  ↳ {japanese}\n", "japanese")
            self.text_area.see(tk.END)
        self.root.after(0, _update)

    def translate_task(self, sentence):
        translated = sentence
        try:
            if self.openai_client:
                res = self.openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "Simultaneous interpreter. JP->EN. Output ONLY English."},
                        {"role": "user", "content": sentence}
                    ],
                    max_tokens=100
                )
                translated = res.choices[0].message.content.strip()
        except Exception as e: print(f"Translate Error: {e}")
        self.append_text(sentence, translated)

    def start_deepgram(self):
        print(f"Connecting to Deepgram... (Using {self.input_device.name})")
        try:
            deepgram = DeepgramClient(api_key=DEEPGRAM_API_KEY)
            
            with deepgram.listen.v1.connect(
                model="nova-2",
                language="ja",
                smart_format="true",
                encoding="linear16",
                channels="1",
                sample_rate=str(SAMPLE_RATE),
                endpointing="500"  # Wait 500ms of silence before closing a segment
            ) as dg_connection:

                def on_message(result):
                    if hasattr(result, "channel") and getattr(result, "is_final", False):
                        sentence = result.channel.alternatives[0].transcript
                        if len(sentence.strip()) > 1:
                            print(f"JP: {sentence}")
                            self.executor.submit(self.translate_task, sentence)

                def on_error(error):
                    print(f"Deepgram Error: {error}")

                dg_connection.on(EventType.MESSAGE, on_message)
                dg_connection.on(EventType.ERROR, on_error)

                # Start listening thread
                threading.Thread(target=dg_connection.start_listening, daemon=True).start()

                print("Deepgram Active. Recording...")
                with self.input_device.recorder(samplerate=SAMPLE_RATE) as rec:
                    last_heartbeat = time.time()
                    while self.is_running:
                        data = rec.record(numframes=int(SAMPLE_RATE * 0.2)) # 200ms
                        if data.shape[1] > 1: data = data.mean(axis=1)
                        else: data = data.squeeze()
                        
                        # Heartbeat to terminal
                        if DEBUG_AUDIO and time.time() - last_heartbeat > 3:
                            peak = np.max(np.abs(data))
                            print(f"[Audio Flowing] Peak: {peak:.4f} (Boosted: {peak*GAIN_BOOST:.4f})")
                            last_heartbeat = time.time()

                        # Apply Gain Boost for Zoom
                        data = data * GAIN_BOOST
                        data = np.clip(data, -1.0, 1.0) # Prevent clipping
                        
                        audio_data = (data * 32767).astype(np.int16).tobytes()
                        dg_connection.send_media(audio_data)
                
                # Connection closes automatically when with block ends

        except Exception as e:
            print(f"Deepgram Loop Error: {e}")

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    TranslatorHUD().run()