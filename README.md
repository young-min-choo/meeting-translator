# Meeting Translator HUD 🇯🇵 ➡️ 🇺🇸

A real-time, "Heads-Up Display" (HUD) translation tool for meetings. It captures system or microphone audio, translates Japanese (or other languages) to English using the OpenAI Whisper API, and displays the subtitles in a transparent, click-through overlay window.

![Status](https://img.shields.io/badge/Status-Beta-green)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue)

## ✨ Features

*   **Always-on-Top Overlay:** Floating subtitle window that stays above Zoom/Teams/Meet.
*   **High Accuracy:** Uses OpenAI's `whisper-1` model via API for near-human translation quality.
*   **Threaded Recording:** No audio loss; records continuously while processing.
*   **Silence Filtering:** intelligent RMS energy detection prevents hallucinations during quiet moments.
*   **Auto-Logging:** Saves a transcript of the meeting to `meeting_log_api.txt`.

## 🛠️ Prerequisites

### System Libraries (Linux)
This tool relies on `soundcard` (Audio) and `tkinter` (GUI). You must install the underlying system drivers:

```bash
sudo apt-get update
sudo apt-get install libpulse-dev portaudio19-dev python3-tk -y
```

### API Key
You need an **OpenAI API Key** to use the translation engine.
[Get one here](https://platform.openai.com/api-keys).

## 🚀 Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/yourusername/meeting-translator.git
    cd meeting-translator
    ```

2.  **Set up Virtual Environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install Python Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure API Key:**
    Create a `.env` file in the project root:
    ```bash
    touch .env
    ```
    Add your key:
    ```env
    OPENAI_API_KEY=sk-your-actual-api-key-here
    ```

## 🎮 Usage

Run the HUD overlay:

```bash
source venv/bin/activate
python gui_overlay.py
```

### Controls
*   **Left Click & Drag:** Move the window.
*   **Right Click:** Exit the application.
*   **Logs:** Check `meeting_log_api.txt` for the full transcript after the meeting.

## 📂 Project Structure

*   `gui_overlay.py` - **Main Application**. The GUI HUD with threaded recording/API logic.
*   `live_api.py` - CLI version of the API translator (no GUI).
*   `live_dual.py` - (Experimental) Local offline mode with Japanese + English display.
*   `requirements.txt` - Python dependencies.

## 🤝 Contributing

Feel free to open issues or PRs if you want to add support for local LLMs or different GUI frameworks!
