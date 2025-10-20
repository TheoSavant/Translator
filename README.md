# 🌍 Universal Live Translator — Professional Edition v3.5

A professional, GPU-accelerated real-time translation application with Netflix/Google-level UI design and continuous speech recognition.

## ✨ Features

### 🎨 Professional UI
- **Material Design 3** glassmorphic overlay with smooth animations
- **Netflix-style** resizable captions overlay
- **Fully customizable** appearance (colors, fonts, sizes)
- **Always-on-top** translucent window with drag & resize

### 🎙️ Advanced Speech Recognition
- **Continuous listening** - never stops, speak naturally
- **Multiple engines** supported:
  - Google Speech Recognition (online)
  - Whisper (offline, GPU-accelerated)
  - Vosk (offline, lightweight)
- **Microphone & System Audio** capture support
- **GPU acceleration** (CUDA/MPS) for 10-20x faster processing

### 🌐 Translation
- **Multi-level caching** for instant repeated translations
- **Online & Offline** modes (Google Translate + Argos)
- **Auto language detection**
- **90+ languages** supported
- **Translation history** with search and export

### 🔊 Text-to-Speech
- **Auto-speak** translated text
- **Volume control** and voice rate adjustment
- **Online (gTTS)** and **offline (pyttsx3)** modes

### ⚡ Performance
- **Async pipeline** with parallel processing
- **ThreadPoolExecutor** for non-blocking operations
- **Real-time performance monitoring**
- **Optimized memory** and cache management

## 📦 Installation

### Prerequisites
- Python 3.8 or higher
- (Optional) CUDA-capable GPU for accelerated Whisper transcription

### Quick Start

1. **Clone the repository**
```bash
git clone <repository-url>
cd universal-translator
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Run the application**
```bash
python main.py
```

The application will automatically check for missing dependencies and offer to install them on first run.

### System-Specific Setup

#### Windows
For system audio capture, enable "Stereo Mix":
1. Right-click speaker icon → Sounds
2. Recording tab → Right-click → Show Disabled Devices
3. Enable "Stereo Mix" or "Wave Out Mix"

#### macOS
Install a virtual audio device for system audio capture:
```bash
brew install blackhole-2ch
# or download from: https://existential.audio/blackhole/
```

#### Linux
Use PulseAudio monitor device (usually available by default)

## 🚀 Usage

### Basic Operation

1. **Start the application** - The main window and overlay will appear
2. **Select languages** - Choose source and target languages from dropdowns
3. **Choose input mode**:
   - 🎙️ **Microphone** - Capture speech from microphone
   - 🎧 **System Audio** - Capture audio from applications (music, videos, calls)
4. **Select recognition engine**:
   - **Google** - Online, accurate, requires internet
   - **Whisper** - Offline, GPU-accelerated, very accurate
   - **Vosk** - Offline, lightweight, fast
5. **Press Start** - Begin continuous listening and translation

### Overlay Features

- **Drag to move** - Click and drag anywhere to reposition
- **Resize** - Drag corners or edges to resize
- **Auto-scroll** - Netflix-style live captions with smooth scrolling
- **Customizable** - Adjust colors, fonts, and transparency in settings

### Keyboard Shortcuts

- **F1** - Show help
- **Ctrl+S** - Open settings
- **Ctrl+H** - View translation history
- **Ctrl+M** - Manage models (Whisper/Vosk)
- **Ctrl+Q** - Quit application

## ⚙️ Configuration

All settings are saved automatically in `~/.universal_translator/translator_config.json`

### Key Settings

- **Recognition Engine** - Choose between Google, Whisper, or Vosk
- **Whisper Model** - Select size (tiny, base, small, medium, large)
- **GPU Acceleration** - Enable/disable GPU usage
- **Live Captions Mode** - Netflix-style smooth scrolling
- **Subtitle Lines** - Number of lines to display (1-5)
- **Auto Speak** - Automatically speak translations
- **Cache Translations** - Enable multi-level caching

## 🏗️ Project Structure

```
universal-translator/
├── main.py                 # Application entry point
├── requirements.txt        # Python dependencies
├── README.md              # This file
│
├── config/                # Configuration management
│   ├── __init__.py
│   ├── constants.py       # Constants and defaults
│   └── config_manager.py  # Config loading/saving
│
├── utils/                 # Utility modules
│   ├── __init__.py
│   ├── gpu_manager.py     # GPU detection and management
│   ├── audio_device_manager.py  # Audio device handling
│   └── helpers.py         # Helper functions
│
├── database/              # Database management
│   ├── __init__.py
│   └── database_manager.py  # Translation history and caching
│
├── models/                # Model managers
│   ├── __init__.py
│   ├── whisper_manager.py  # Whisper model loading
│   └── vosk_manager.py    # Vosk model management
│
├── core/                  # Core functionality
│   ├── __init__.py
│   ├── translation_engine.py  # Translation with caching
│   ├── tts_manager.py     # Text-to-speech
│   └── speech_recognition.py  # Continuous recognition
│
└── ui/                    # User interface
    ├── __init__.py
    ├── overlay.py         # Resizable overlay window
    ├── settings_dialog.py # Settings configuration
    ├── model_manager_dialog.py  # Model downloads
    └── main_window.py     # Main application window
```

## 🔧 Advanced Features

### GPU Acceleration

The application automatically detects and uses:
- **CUDA** (NVIDIA GPUs) - Provides 10-20x speedup for Whisper
- **MPS** (Apple Silicon) - Native GPU acceleration on M1/M2 Macs
- **CPU fallback** - Works on all systems

### Multi-Level Translation Caching

1. **In-memory cache** - Ultra-fast (~0ms) for recent translations
2. **Database cache** - Fast (~5-10ms) for all cached translations
3. **Online/Offline translation** - Automatic fallback

### Model Management

- **Whisper models** - Download different sizes (tiny to large)
- **Vosk models** - Download language-specific models
- **Automatic caching** - Models downloaded once, reused forever

## 📊 Performance

- **Recognition latency**: 100-500ms (GPU) / 500-2000ms (CPU)
- **Translation latency**: 0-50ms (cached) / 100-300ms (online)
- **Memory usage**: ~500MB (base) + model size
- **GPU memory**: 1-4GB depending on Whisper model size

## 🐛 Troubleshooting

### "No loopback device found"
- **Windows**: Enable Stereo Mix in sound settings
- **macOS**: Install BlackHole or Soundflower
- **Linux**: Check PulseAudio monitor devices

### "CUDA not detected"
- Install NVIDIA drivers and CUDA toolkit
- Reinstall PyTorch with CUDA support:
  ```bash
  pip install torch --extra-index-url https://download.pytorch.org/whl/cu118
  ```

### "Model download failed"
- Check internet connection
- Try downloading manually from Vosk/Whisper model repositories
- Check available disk space (~500MB-2GB per model)

### High CPU/Memory usage
- Use smaller Whisper model (tiny/base instead of large)
- Disable GPU if it's causing issues
- Reduce max words in overlay settings

## 📝 License

This project is provided as-is for educational and personal use.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for bugs and feature requests.

## 🙏 Acknowledgments

- [Whisper](https://github.com/openai/whisper) by OpenAI
- [Vosk](https://alphacephei.com/vosk/) speech recognition toolkit
- [Deep Translator](https://github.com/nidhaloff/deep-translator)
- [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) for the UI framework

## 📧 Support

For issues, questions, or suggestions, please open an issue on the GitHub repository.

---

**Made with ❤️ for the global community**
