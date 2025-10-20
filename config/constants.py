"""
Configuration constants and default settings for Universal Live Translator
"""
from pathlib import Path
from enum import Enum

# Directory structure
BASE_DIR = Path.home() / ".universal_translator"
BASE_DIR.mkdir(exist_ok=True, parents=True)

DB_FILE = BASE_DIR / "translator_history.db"
AUDIO_DIR = BASE_DIR / "audio_cache"
VOSK_MODELS_DIR = BASE_DIR / "vosk_models"
CONFIG_FILE = BASE_DIR / "translator_config.json"

AUDIO_DIR.mkdir(exist_ok=True)
VOSK_MODELS_DIR.mkdir(exist_ok=True)

class RecognitionEngine(Enum):
    """Speech recognition engine options"""
    GOOGLE = "google"
    VOSK = "vosk"
    WHISPER = "whisper"

# Vosk model download URLs
VOSK_MODELS = {
    "en": "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip",
    "fr": "https://alphacephei.com/vosk/models/vosk-model-small-fr-0.22.zip",
    "es": "https://alphacephei.com/vosk/models/vosk-model-small-es-0.42.zip",
    "de": "https://alphacephei.com/vosk/models/vosk-model-small-de-0.15.zip",
}

# Whisper model sizes
WHISPER_MODELS = ["tiny", "base", "small", "medium", "large"]

# Default configuration
DEFAULT_CONFIG = {
    "theme": "dark",
    "overlay_position": [100, 100, 850, 180],
    "overlay_visible": True,
    "font_size": 22,
    "text_color": "#FFFFFF",
    "bg_color": "rgba(15,15,20,0.92)",
    "max_words": 150,
    "auto_speak": True,
    "tts_rate": 160,
    "volume": 0.75,
    "cache_translations": True,
    "cache_expiry_days": 14,
    "source_language": "auto",
    "target_language": "fr",
    "show_confidence": True,
    "recognition_engine": "google",
    "whisper_model": "base",
    "audio_device_input": "default",
    "use_gpu": True,
    "animation_duration": 250,
    "live_captions_mode": True,
    "subtitle_lines": 3,
    "subtitle_update_delay": 8,  # milliseconds between word updates
    # Enhanced features (v4.0)
    "conversation_mode_enabled": False,  # Bidirectional auto-translation
    "conversation_auto_mode": False,  # Auto-detect any language pair
    "slang_translation_enabled": True,  # Translate slang and abbreviations
    "contextual_translation": True,  # Use contextual awareness
    # Voice duplication and translation modes (v4.5)
    "translation_mode": "standard",  # standard, simultaneous, universal, voice_duplication
    "voice_duplication_enabled": False,  # Enable RVC voice cloning
    "active_rvc_model": None,  # Current active RVC model name
    "rvc_pitch_shift": 0,  # Voice pitch adjustment (-12 to 12)
    "rvc_index_rate": 0.75,  # Index search ratio (0.0 to 1.0)
    # Platform integrations
    "enabled_platforms": [],  # List of enabled platform names (discord, zoom, teams, etc.)
    "virtual_microphone_enabled": False,  # Use virtual microphone for output
    # Gaming and real-time features
    "text_translation_overlay": False,  # Show text translation overlay for gaming
    "real_time_dubbing": False,  # Enable real-time voice dubbing
}

# Required packages for dependency checking
REQUIRED_PACKAGES = [
    "PyQt6", "pyttsx3", "gtts", "argostranslate", "SpeechRecognition",
    "sounddevice", "vosk", "pydub", "langdetect", "deep-translator",
    "simpleaudio", "numpy", "requests", "openai-whisper", "torch", "pyaudio", "scipy"
]
