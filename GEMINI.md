# Meeting Translator - Project Plan

## 🟢 Status: Phase 3 - The Overlay UI
**Last Updated:** February 2, 2026

### Current Progress:
- [x] **Environment:** Python venv + System Audio Drivers (`libpulse`).
- [x] **Logic:** Verified `live_api.py` using OpenAI Whisper API provides perfect quality.
- [x] **Pivot:** Abandoned local CPU processing due to lag; Cloud API is the chosen solution.

### Next Steps:
- [ ] **GUI:** Build a transparent "Heads-Up Display" (HUD) using `Tkinter`.
- [ ] **Settings:** Add a config menu to save the API Key permanently.
- [ ] **Packaging:** Create a desktop shortcut.

### Hardware Context:
- **Primary:** Laptop Microphone / System Loopback.
- **Secondary:** Anker Speaker (pluggable via USB/Jack).

---

## 1. Overview
... (rest of the file remains the same)
A real-time meeting assistant designed to transcribe and translate Japanese speech into English text.
**Core Goal:** Provide a "Heads Up Display" (HUD) for English speakers in Japanese-dominant meetings.

## 2. Modes of Operation
To support both Remote and In-Person scenarios, the system requires a **Dual-Source Audio Engine**:

### 🎧 Mode A: Telepresence (Zoom/Meets)
*   **Source:** System Audio Monitor (Loopback).
*   **Use Case:** User is wearing headphones; meeting is digital. The app listens to the incoming audio stream from the conference software.

### 🎙️ Mode B: The Room (In-Person)
*   **Source:** Physical Microphone.
*   **Use Case:** User is in a physical conference room. The laptop (or external mic) captures the ambient conversation.
*   **Challenge:** Higher noise floor, reverb, distant voices. Requires robust VAD (Voice Activity Detection).

## 3. Architecture

### Layer 1: The Ear (Audio Capture)
*   **Library:** `soundcard` (Cross-platform, easy loopback) or `PyAudio`.
*   **Component:** `AudioStreamer` class that accepts a `device_id`.
*   **Processing:**
    *   **VAD:** `silero-vad` to filter silence and noise.
    *   **Buffering:** Accumulate audio chunks into valid speech segments (2-5 seconds) to prevent cutting words.

### Layer 2: The Brain (Transcription & Translation)
*   **Transcription:** `faster-whisper` (Local).
    *   Model: `small` or `medium` (Balance speed/accuracy).
    *   *Optimization:* Run on CPU with `int8` quantization if GPU unavailable.
*   **Translation:**
    *   **Option A (Fast/Rough):** Direct Whisper translation (Enables `task="translate"`).
    *   **Option B (High Quality):** Transcribe to Japanese first, then send text to LLM (OpenAI/Anthropic) for context-aware translation.
    *   *Selection:* We will implement Option A first for speed, with a toggle for Option B.

### Layer 3: The Face (UI)
*   **Framework:** `Tkinter` (Python standard) or `PyQt6`.
*   **Design:**
    *   Transparent, frameless window.
    *   "Click-through" ability (optional).
    *   Auto-scrolling text.
    *   **Control Panel:** Separate window to select Audio Source (Mode A/B) and Model size.

## 4. Roadmap

### ✅ Phase 1: Environment & Audio Test
*   [ ] Initialize Project & Git.
*   [ ] Set up `venv` and `requirements.txt`.
*   [ ] Create `list_devices.py` to identify Mic vs. Loopback inputs.
*   [ ] Create `record_test.py` to verify capture from both sources.

### 🚧 Phase 2: Transcription Core
*   [ ] Implement `faster-whisper`.
*   [ ] Pipe audio buffer to Whisper.
*   [ ] Output raw text to console.

### 🔮 Phase 3: The Overlay UI
*   [ ] Build transparent window.
*   [ ] Connect Transcription stream to UI.

### 🚀 Phase 4: Polish & Translation
*   [ ] Integrate LLM translation (optional).
*   [ ] Add "Pause/Resume" toggle.
*   [ ] Package for distribution (optional).
