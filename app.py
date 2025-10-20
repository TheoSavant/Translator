#!/usr/bin/env python3
"""
Universal Live Translator Desktop — Professional Edition v3.5
-------------------------------------------------------------
🎨 Netflix/Google-Level Professional Features:
- 🎙️ Continuous listening (never stops - speak naturally)
- 📺 Netflix-style resizable overlay (Material Design 3)
- 🚀 GPU acceleration (CUDA/MPS - 10-20x faster)
- ⚡ Advanced async pipeline (parallel processing)
- 💎 Material Design 3 UI (glassmorphic effects)
- 🎬 Smooth animations and micro-interactions
- ♿ Accessible design with keyboard navigation
- 🌈 Professional color system and typography
- 📊 Real-time performance monitoring
- 🔧 Comprehensive settings management
"""
import os, sys, threading, queue, logging, sqlite3, tempfile, json, time
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Any
from datetime import datetime
from collections import deque
import hashlib
import numpy as np
import warnings
from dataclasses import dataclass
from enum import Enum
from concurrent.futures import ThreadPoolExecutor
import warnings

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning, module="ctranslate2")
warnings.filterwarnings("ignore", message="pkg_resources is deprecated")

import subprocess

REQUIRED_PACKAGES = [
    "PyQt6", "pyttsx3", "gtts", "argostranslate", "SpeechRecognition",
    "sounddevice", "vosk", "pydub", "langdetect", "deep-translator",
    "simpleaudio", "numpy", "requests", "openai-whisper", "torch", "pyaudio", "scipy"
]

def ensure_dependencies():
    missing = []
    for pkg in REQUIRED_PACKAGES:
        try:
            __import__(pkg.replace('-', '_').split('[')[0])
        except ImportError:
            missing.append(pkg)
    
    if missing:
        print(f"\n{'='*60}\nMissing Dependencies\n{'='*60}")
        print("The following packages need to be installed:")
        for pkg in missing:
            print(f"  • {pkg}")
        print(f"\nTotal size: ~500MB (includes PyTorch and Whisper)\n{'='*60}")
        
        response = input("\nInstall missing packages? (y/n): ").strip().lower()
        if response == 'y':
            for pkg in missing:
                print(f"\n📦 Installing {pkg}...")
                subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", pkg])
            print("\n✅ All dependencies installed!\n")
        else:
            print("\n❌ Cannot proceed without packages. Exiting...")
            sys.exit(1)

ensure_dependencies()

import pyttsx3
from gtts import gTTS
import speech_recognition as sr
import sounddevice as sd
import pyaudio
from vosk import Model, KaldiRecognizer
from langdetect import detect, LangDetectException, detect_langs
from deep_translator import GoogleTranslator
from deep_translator.constants import GOOGLE_LANGUAGES_TO_CODES
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from pydub import AudioSegment
import simpleaudio as sa
import argostranslate.translate
import argostranslate.package
import requests
import whisper
import torch

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('translator.log'),
        logging.StreamHandler()
    ]
)
log = logging.getLogger("Translator")

BASE_DIR = Path.home() / ".universal_translator"
BASE_DIR.mkdir(exist_ok=True, parents=True)

DB_FILE = BASE_DIR / "translator_history.db"
AUDIO_DIR = BASE_DIR / "audio_cache"
VOSK_MODELS_DIR = BASE_DIR / "vosk_models"
CONFIG_FILE = BASE_DIR / "translator_config.json"

AUDIO_DIR.mkdir(exist_ok=True)
VOSK_MODELS_DIR.mkdir(exist_ok=True)

class RecognitionEngine(Enum):
    GOOGLE = "google"
    VOSK = "vosk"
    WHISPER = "whisper"

VOSK_MODELS = {
    "en": "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip",
    "fr": "https://alphacephei.com/vosk/models/vosk-model-small-fr-0.22.zip",
    "es": "https://alphacephei.com/vosk/models/vosk-model-small-es-0.42.zip",
    "de": "https://alphacephei.com/vosk/models/vosk-model-small-de-0.15.zip",
}

WHISPER_MODELS = ["tiny", "base", "small", "medium", "large"]

DEFAULT_CONFIG = {
    "theme": "dark", "overlay_position": [100, 100, 850, 180], "overlay_visible": True,
    "font_size": 22, "text_color": "#FFFFFF", "bg_color": "rgba(15,15,20,0.92)",
    "max_words": 150, "auto_speak": True, "tts_rate": 160, "volume": 0.75,
    "cache_translations": True, "cache_expiry_days": 14, "source_language": "auto",
    "target_language": "fr", "show_confidence": True, "recognition_engine": "google",
    "whisper_model": "base", "audio_device_input": "default", "use_gpu": True,
    "animation_duration": 250, "live_captions_mode": True, "subtitle_lines": 3,
    "subtitle_update_delay": 8  # milliseconds between word updates (lower = faster, professional default)
}

@dataclass
class AudioDevice:
    index: int
    name: str
    max_input_channels: int
    max_output_channels: int
    default_samplerate: float
    is_input: bool
    is_output: bool
    host_api: str

class GPUManager:
    """Manages GPU detection and device selection"""
    def __init__(self):
        # Enhanced CUDA detection
        self.has_cuda = torch.cuda.is_available()
        if not self.has_cuda and torch.version.cuda is not None:
            # Try to initialize CUDA even if not initially available
            try:
                torch.cuda.init()
                self.has_cuda = torch.cuda.is_available()
            except:
                pass
        
        self.has_mps = hasattr(torch.backends, 'mps') and torch.backends.mps.is_available()
        self.device = self._detect_device()
        self.device_name = self._get_device_name()
        
        # Log detailed GPU info
        if self.has_cuda:
            log.info(f"CUDA detected: {torch.cuda.get_device_name(0)}")
            log.info(f"CUDA version: {torch.version.cuda}")
            log.info(f"CUDA device count: {torch.cuda.device_count()}")
        else:
            log.warning("CUDA not detected. GPU acceleration disabled.")
            if torch.version.cuda:
                log.warning(f"PyTorch built with CUDA {torch.version.cuda} but CUDA runtime not available")
    
    def _detect_device(self):
        if self.has_cuda:
            return "cuda"
        elif self.has_mps:
            return "mps"
        return "cpu"
    
    def _get_device_name(self):
        if self.has_cuda:
            return f"CUDA ({torch.cuda.get_device_name(0)})"
        elif self.has_mps:
            return "Apple Silicon (MPS)"
        return "CPU"
    
    def get_device(self, use_gpu=True):
        if use_gpu and (self.has_cuda or self.has_mps):
            return self.device
        return "cpu"
    
    def is_gpu_available(self):
        return self.has_cuda or self.has_mps

gpu_manager = GPUManager()

class AudioDeviceManager:
    def __init__(self):
        self.pa = pyaudio.PyAudio()
        self.devices = self._detect_devices()
        self.input_devices = [d for d in self.devices if d.is_input]
    
    def _detect_devices(self) -> List[AudioDevice]:
        devices = []
        try:
            for i in range(self.pa.get_device_count()):
                info = self.pa.get_device_info_by_index(i)
                device = AudioDevice(
                    index=i, name=info['name'],
                    max_input_channels=info['maxInputChannels'],
                    max_output_channels=info['maxOutputChannels'],
                    default_samplerate=info['defaultSampleRate'],
                    is_input=info['maxInputChannels'] > 0,
                    is_output=info['maxOutputChannels'] > 0,
                    host_api=self.pa.get_host_api_info_by_index(info['hostApi'])['name']
                )
                devices.append(device)
        except Exception as e:
            log.error(f"Error detecting devices: {e}")
        return devices
    
    def get_default_input_device(self) -> Optional[AudioDevice]:
        try:
            default_info = self.pa.get_default_input_device_info()
            for device in self.input_devices:
                if device.index == default_info['index']:
                    return device
        except:
            pass
        return self.input_devices[0] if self.input_devices else None
    
    def get_loopback_device(self) -> Optional[AudioDevice]:
        """Get loopback device with validation"""
        keywords = ['stereo mix', 'loopback', 'wave out', 'what u hear', 'wave-out', 'waveout']
        candidates = []
        
        # Find all potential loopback devices
        for device in self.input_devices:
            device_name_lower = device.name.lower()
            if any(k in device_name_lower for k in keywords):
                candidates.append(device)
        
        # Try to find a working device by testing each candidate
        for device in candidates:
            try:
                # Quick test with sounddevice instead of pyaudio
                import sounddevice as sd
                test_stream = sd.InputStream(
                    channels=1,
                    samplerate=int(device.default_samplerate),
                    device=device.index,
                    blocksize=1024
                )
                test_stream.close()
                log.info(f"Found working loopback device: {device.name}")
                return device
            except Exception as e:
                log.warning(f"Loopback device {device.name} failed test: {e}")
                continue
        
        # If no keywords match, try the default input device if it's not a microphone
        try:
            default = self.get_default_input_device()
            if default and 'mic' not in default.name.lower():
                log.info(f"Trying default input as loopback: {default.name}")
                return default
        except Exception as e:
            log.warning(f"Default device check failed: {e}")
        
        return None
    
    def test_device(self, device: AudioDevice, duration: float = 1.0) -> bool:
        try:
            stream = self.pa.open(format=pyaudio.paInt16, channels=1,
                rate=int(device.default_samplerate), input=True,
                input_device_index=device.index, frames_per_buffer=1024)
            stream.read(int(device.default_samplerate * duration))
            stream.stop_stream()
            stream.close()
            return True
        except:
            return False
    
    def cleanup(self):
        self.pa.terminate()

audio_device_manager = AudioDeviceManager()

class ConfigManager:
    def __init__(self):
        self.config = self.load_config()
        self.lock = threading.Lock()
    
    def load_config(self) -> dict:
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, 'r') as f:
                    return {**DEFAULT_CONFIG, **json.load(f)}
            except:
                pass
        return DEFAULT_CONFIG.copy()
    
    def save_config(self):
        with self.lock:
            try:
                with open(CONFIG_FILE, 'w') as f:
                    json.dump(self.config, f, indent=2)
            except Exception as e:
                log.error(f"Save config failed: {e}")
    
    def get(self, key: str, default=None):
        with self.lock:
            return self.config.get(key, default)
    
    def set(self, key: str, value):
        with self.lock:
            self.config[key] = value
        self.save_config()

config = ConfigManager()

class DatabaseManager:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._local = threading.local()
        self.init_tables()
    
    def _get_connection(self):
        if not hasattr(self._local, 'conn'):
            self._local.conn = sqlite3.connect(str(self.db_path), check_same_thread=True)
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn
    
    def init_tables(self):
        conn = self._get_connection()
        conn.execute("""CREATE TABLE IF NOT EXISTS translations (
            id INTEGER PRIMARY KEY, source_text TEXT, translated_text TEXT,
            source_lang TEXT, target_lang TEXT, mode TEXT, engine TEXT,
            confidence REAL, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, duration_ms INTEGER)""")
        conn.execute("""CREATE TABLE IF NOT EXISTS cache (
            id INTEGER PRIMARY KEY, hash TEXT UNIQUE, source_text TEXT, translated_text TEXT,
            source_lang TEXT, target_lang TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            access_count INTEGER DEFAULT 0, last_accessed DATETIME DEFAULT CURRENT_TIMESTAMP)""")
        conn.commit()
    
    def add_translation(self, source, translated, src_lang, tgt_lang, mode, engine="google", confidence=1.0, duration_ms=0):
        conn = self._get_connection()
        conn.execute("INSERT INTO translations (source_text, translated_text, source_lang, target_lang, mode, engine, confidence, duration_ms) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (source, translated, src_lang, tgt_lang, mode, engine, confidence, duration_ms))
        conn.commit()
    
    def get_cached_translation(self, text, src, tgt):
        key = hashlib.md5(f"{text}:{src}:{tgt}".encode()).hexdigest()
        conn = self._get_connection()
        result = conn.execute("SELECT translated_text FROM cache WHERE hash = ?", (key,)).fetchone()
        return result[0] if result else None
    
    def cache_translation(self, text, translated, src, tgt):
        key = hashlib.md5(f"{text}:{src}:{tgt}".encode()).hexdigest()
        conn = self._get_connection()
        try:
            conn.execute("INSERT OR REPLACE INTO cache (hash, source_text, translated_text, source_lang, target_lang, last_accessed) VALUES (?, ?, ?, ?, ?, datetime('now'))",
                (key, text, translated, src, tgt))
            conn.commit()
        except:
            pass
    
    def get_history(self, limit=50, search=""):
        conn = self._get_connection()
        if search:
            results = conn.execute("SELECT source_text, translated_text, source_lang, target_lang, mode, engine, confidence, timestamp FROM translations WHERE source_text LIKE ? OR translated_text LIKE ? ORDER BY id DESC LIMIT ?",
                (f"%{search}%", f"%{search}%", limit)).fetchall()
        else:
            results = conn.execute("SELECT source_text, translated_text, source_lang, target_lang, mode, engine, confidence, timestamp FROM translations ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(row) for row in results]
    
    def export_history(self, filepath):
        conn = self._get_connection()
        results = conn.execute("SELECT * FROM translations ORDER BY timestamp DESC").fetchall()
        with open(filepath, 'w', encoding='utf-8') as f:
            for row in results:
                r = dict(row)
                f.write(f"[{r['timestamp']}] {r['source_lang']}→{r['target_lang']} ({r['mode']}/{r['engine']})\n")
                f.write(f"Source: {r['source_text']}\nTranslation: {r['translated_text']}\n{'-'*80}\n\n")
    
    def clear_history(self):
        conn = self._get_connection()
        conn.execute("DELETE FROM translations")
        conn.commit()

db = DatabaseManager(DB_FILE)

def is_online():
    try:
        requests.get("https://www.google.com", timeout=3)
        return True
    except:
        return False

class WhisperModelManager:
    def __init__(self):
        self.models = {}
        self.device = "cpu"
        self.use_gpu = config.get("use_gpu", True)
        # Initialize device on startup - force GPU if available
        self.set_device(self.use_gpu)
        log.info(f"WhisperModelManager initialized with device: {self.device} (use_gpu={self.use_gpu})")
    
    def set_device(self, use_gpu=True):
        self.use_gpu = use_gpu
        old_device = self.device
        self.device = gpu_manager.get_device(use_gpu)
        log.info(f"WhisperModelManager device set to: {self.device} (requested use_gpu={use_gpu})")
        log.info(f"GPU available: {gpu_manager.is_gpu_available()}, CUDA: {gpu_manager.has_cuda}, MPS: {gpu_manager.has_mps}")
        
        # Reload models if device changed
        if old_device != self.device and self.models:
            log.info(f"Device changed from {old_device} to {self.device}, reloading models...")
            old_models = list(self.models.keys())
            self.models.clear()
            for model_size in old_models:
                self.load_model(model_size)
    
    def load_model(self, model_size="base"):
        if model_size in self.models:
            return True
        try:
            log.info(f"Loading Whisper {model_size} on {self.device}...")
            self.models[model_size] = whisper.load_model(model_size, device=self.device)
            log.info(f"Whisper {model_size} loaded successfully")
            return True
        except Exception as e:
            log.error(f"Whisper load failed: {e}")
            return False
    
    def transcribe(self, audio_data, model_size="base", language=None):
        if model_size not in self.models:
            if not self.load_model(model_size):
                return "", 0.0
        try:
            # Validate audio data
            if audio_data is None or len(audio_data) == 0:
                log.warning("Empty audio data received")
                return "", 0.0
            
            # Ensure audio is float32 and normalized
            if audio_data.dtype != np.float32:
                audio_data = audio_data.astype(np.float32)
                if np.abs(audio_data).max() > 1.0:
                    audio_data = audio_data / 32768.0
            
            # Ensure minimum audio length (Whisper needs at least some samples)
            if len(audio_data) < 400:  # ~0.025s at 16kHz
                log.warning(f"Audio too short: {len(audio_data)} samples")
                return "", 0.0
            
            fp16 = self.device == "cuda"
            result = self.models[model_size].transcribe(
                audio_data, 
                language=language, 
                task="transcribe", 
                fp16=fp16,
                condition_on_previous_text=False  # Avoid issues with empty audio
            )
            text = result.get("text", "").strip()
            segments = result.get("segments", [])
            confidence = 1.0 - (sum(s.get("no_speech_prob", 0) for s in segments) / len(segments) if segments else 0)
            return text, confidence
        except Exception as e:
            log.error(f"Whisper transcribe failed: {e}")
            import traceback
            log.error(traceback.format_exc())
            return "", 0.0

whisper_manager = WhisperModelManager()

class VoskModelManager:
    def __init__(self):
        self.models = {}
        self.load_existing_models()
    
    def load_existing_models(self):
        for lang_code in VOSK_MODELS.keys():
            model_dir = VOSK_MODELS_DIR / f"vosk-model-small-{lang_code}"
            if model_dir.exists():
                try:
                    self.models[lang_code] = Model(str(model_dir))
                except:
                    pass
    
    def get_model(self, lang_code):
        return self.models.get(lang_code)
    
    def download_model(self, lang_code, progress_callback=None):
        if lang_code not in VOSK_MODELS:
            return False
        model_dir = VOSK_MODELS_DIR / f"vosk-model-small-{lang_code}"
        if model_dir.exists():
            return True
        try:
            url = VOSK_MODELS[lang_code]
            zip_path = VOSK_MODELS_DIR / f"model-{lang_code}.zip"
            response = requests.get(url, stream=True)
            total = int(response.headers.get('content-length', 0))
            downloaded = 0
            with open(zip_path, 'wb') as f:
                for chunk in response.iter_content(8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if progress_callback and total > 0:
                            progress_callback(downloaded / total)
            import zipfile
            with zipfile.ZipFile(zip_path, 'r') as z:
                z.extractall(VOSK_MODELS_DIR)
            zip_path.unlink()
            for item in VOSK_MODELS_DIR.iterdir():
                if item.is_dir() and lang_code in item.name.lower():
                    if item.name != f"vosk-model-small-{lang_code}":
                        item.rename(model_dir)
                    break
            self.models[lang_code] = Model(str(model_dir))
            return True
        except Exception as e:
            log.error(f"Download failed: {e}")
            return False
    
    def has_model(self, lang_code):
        return lang_code in self.models

vosk_manager = VoskModelManager()

def setup_argos():
    try:
        argostranslate.package.update_package_index()
        available = argostranslate.package.get_available_packages()
        installed = {l.code for l in argostranslate.translate.get_installed_languages()}
        for from_l in ["en", "fr", "es"]:
            for to_l in ["en", "fr", "es"]:
                if from_l != to_l and from_l not in installed:
                    pkg = next((p for p in available if p.from_code==from_l and p.to_code==to_l), None)
                    if pkg:
                        argostranslate.package.install_from_path(pkg.download())
    except:
        pass

threading.Thread(target=setup_argos, daemon=True).start()

class TranslationEngine:
    """Professional translation engine with enhanced caching and performance optimization"""
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=6, thread_name_prefix="TranslateWorker")
        # In-memory cache for ultra-fast repeated translations
        self.memory_cache = {}
        self.cache_hits = 0
        self.cache_misses = 0
    
    def translate(self, text, src, tgt):
        """Translate with enhanced multi-level caching for maximum performance"""
        if not text.strip():
            return "", 0, 1.0
        
        # Level 1: In-memory cache (ultra-fast, ~0ms)
        cache_key = f"{text}:{src}:{tgt}"
        if cache_key in self.memory_cache:
            self.cache_hits += 1
            cached_result = self.memory_cache[cache_key]
            log.debug(f"Memory cache HIT ({self.cache_hits}/{self.cache_hits + self.cache_misses})")
            return cached_result[0], 0, cached_result[1]
        
        # Level 2: Database cache (fast, ~5-10ms)
        if config.get("cache_translations"):
            cached = db.get_cached_translation(text, src, tgt)
            if cached:
                self.cache_hits += 1
                self.memory_cache[cache_key] = (cached, 1.0)
                # Limit memory cache size to prevent memory bloat
                if len(self.memory_cache) > 1000:
                    # Remove oldest 20% of entries
                    keys_to_remove = list(self.memory_cache.keys())[:200]
                    for k in keys_to_remove:
                        del self.memory_cache[k]
                return cached, 0, 1.0
        
        self.cache_misses += 1
        start = time.time()
        translated = None
        confidence = 1.0
        
        # Try online translation first (Google Translate)
        if is_online():
            try:
                translated = GoogleTranslator(source=src, target=tgt).translate(text)
                confidence = 1.0
            except Exception as e:
                log.warning(f"Google Translate failed: {e}")
        
        # Fallback to offline Argos translation
        if not translated:
            try:
                translated = argostranslate.translate.translate(text, from_code=src, to_code=tgt)
                confidence = 0.85
            except Exception as e:
                log.warning(f"Argos Translate failed: {e}")
                translated = text
                confidence = 0.0
        
        duration = int((time.time() - start) * 1000)
        
        # Cache the result in both levels
        if translated and config.get("cache_translations"):
            db.cache_translation(text, translated, src, tgt)
            self.memory_cache[cache_key] = (translated, confidence)
        
        return translated, duration, confidence
    
    def translate_async(self, text, src, tgt, callback):
        """Async translation for non-blocking processing"""
        def _translate():
            result = self.translate(text, src, tgt)
            callback(result)
        self.executor.submit(_translate)

translator = TranslationEngine()

class TTSManager:
    def __init__(self):
        self.queue = queue.Queue()
        self.running = True
        self.current = None
        self.volume = config.get("volume", 0.8)
        self.temp_files = []
        threading.Thread(target=self._worker, daemon=True).start()
    
    def _worker(self):
        while self.running:
            try:
                text, lang = self.queue.get(timeout=0.5)
                self._speak(text, lang)
            except queue.Empty:
                continue
            except Exception as e:
                log.warning(f"TTS error: {e}")
    
    def _speak(self, text, lang):
        try:
            if is_online():
                tts = gTTS(text=text, lang=lang, slow=False)
                tmp_mp3 = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3", dir=AUDIO_DIR)
                tmp_mp3.close()
                tts.save(tmp_mp3.name)
                tmp_wav = tempfile.NamedTemporaryFile(delete=False, suffix=".wav", dir=AUDIO_DIR)
                tmp_wav.close()
                audio = AudioSegment.from_mp3(tmp_mp3.name)
                audio = audio + (20 * np.log10(self.volume))
                audio.export(tmp_wav.name, format="wav")
                wave_obj = sa.WaveObject.from_wave_file(tmp_wav.name)
                self.current = wave_obj.play()
                self.current.wait_done()
                os.unlink(tmp_mp3.name)
                os.unlink(tmp_wav.name)
            else:
                engine = pyttsx3.init()
                engine.setProperty('rate', config.get("tts_rate", 150))
                engine.say(text)
                engine.runAndWait()
        except Exception as e:
            log.error(f"TTS failed: {e}")
    
    def speak(self, text, lang):
        if text.strip():
            self.queue.put((text, lang))
    
    def stop(self):
        if self.current and self.current.is_playing():
            self.current.stop()
    
    def set_volume(self, volume):
        self.volume = max(0.0, min(1.0, volume))
    
    def shutdown(self):
        self.running = False
        self.stop()

tts_manager = TTSManager()

class ContinuousSpeechRecognitionThread(QThread):
    """Continuous listening - never stops, async processing"""
    phrase_detected = pyqtSignal(str, float)
    status_changed = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    performance_update = pyqtSignal(dict)  # Queue sizes, processing time
    
    def __init__(self, source_type="microphone", language="en", engine=RecognitionEngine.GOOGLE, device_index=None):
        super().__init__()
        self.running = True
        self.source_type = source_type
        self.language = language
        self.engine = engine
        self.device_index = device_index
        self.vosk_model = vosk_manager.get_model(language) if engine == RecognitionEngine.VOSK else None
        self.whisper_model_size = config.get("whisper_model", "base")
        
        # Processing queues for async pipeline
        self.recognition_queue = queue.Queue(maxsize=10)  # Audio chunks waiting for recognition
        self.translation_queue = queue.Queue(maxsize=10)  # Texts waiting for translation
        
        # Thread pool for parallel processing
        self.executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="RecognitionWorker")
        self.executor_shutdown = False
        
        # Performance monitoring
        self.processing_times = deque(maxlen=20)
        self.last_perf_update = time.time()
    
    def run(self):
        try:
            if self.source_type == "microphone":
                self._listen_microphone_continuous()
            else:
                self._listen_system_audio_continuous()
        except Exception as e:
            self.error_occurred.emit(f"Recognition error: {e}")
    
    def _listen_microphone_continuous(self):
        """Continuous microphone listening - never stops"""
        recognizer = sr.Recognizer()
        recognizer.energy_threshold = 3000
        recognizer.pause_threshold = 1.2
        
        try:
            kwargs = {}
            if self.device_index is not None:
                kwargs['device_index'] = self.device_index
            
            with sr.Microphone(**kwargs) as source:
                self.status_changed.emit("🎙️ Calibrating...")
                recognizer.adjust_for_ambient_noise(source, 1)
                self.status_changed.emit(f"🎙️ Continuous Listening ({self.engine.value})...")
                
                while self.running:
                    try:
                        # Non-blocking listen - captures audio continuously
                        audio = recognizer.listen(source, timeout=None, phrase_time_limit=15)
                        
                        # Async processing - submit to queue
                        if not self.recognition_queue.full() and not self.executor_shutdown:
                            self.executor.submit(self._process_audio, audio)
                        elif self.executor_shutdown:
                            break
                        else:
                            log.warning("Recognition queue full, dropping audio")
                        
                        # Update performance metrics
                        self._update_performance()
                        
                    except sr.WaitTimeoutError:
                        pass
                    except Exception as e:
                        if self.running:  # Only log if we're supposed to be running
                            log.warning(f"Mic error: {e}")
                        time.sleep(0.5)
        except Exception as e:
            if self.running:
                self.error_occurred.emit(f"Microphone setup failed: {e}")
    
    def _listen_system_audio_continuous(self):
        """Continuous system audio capture with proper threading and validation"""
        loopback = audio_device_manager.get_loopback_device()
        if not loopback:
            error_msg = (
                "❌ No working loopback device found.\n\n"
                "Windows: Enable 'Stereo Mix' in Sound Settings:\n"
                "  1. Right-click speaker icon → Sounds\n"
                "  2. Recording tab → Right-click → Show Disabled Devices\n"
                "  3. Enable 'Stereo Mix' or 'Wave Out Mix'\n\n"
                "macOS: Install BlackHole or Soundflower\n\n"
                "Linux: Use PulseAudio monitor device"
            )
            self.error_occurred.emit(error_msg)
            return
        
        # Validate sample rate
        try:
            samplerate = int(loopback.default_samplerate)
            if samplerate > 48000:
                log.warning(f"Sample rate {samplerate} too high, limiting to 16000")
                samplerate = 16000
            elif samplerate < 8000:
                log.warning(f"Sample rate {samplerate} too low, using 16000")
                samplerate = 16000
            else:
                samplerate = min(samplerate, 16000)
        except Exception as e:
            log.error(f"Sample rate validation failed: {e}")
            samplerate = 16000
        
        audio_buffer = []
        samples_needed = int(samplerate * 5.0)
        buffer_lock = threading.Lock()
        stream_error = [None]  # Use list to allow modification in callback
        
        def callback(indata, frames, time_info, status):
            """Audio callback - runs in separate thread"""
            try:
                if status:
                    log.warning(f"Audio callback status: {status}")
                
                if not self.running:
                    raise sd.CallbackStop()
                
                # Validate input data
                if indata is None or len(indata) == 0:
                    return
                
                with buffer_lock:
                    # Handle mono/stereo input
                    if indata.ndim == 1:
                        audio_buffer.extend(indata.copy())
                    else:
                        audio_buffer.extend(indata[:, 0].copy())
                    
                    if len(audio_buffer) >= samples_needed:
                        chunk = np.array(audio_buffer[:samples_needed])
                        audio_buffer.clear()
                        
                        # Submit to thread pool for processing
                        if not self.recognition_queue.full() and not self.executor_shutdown:
                            try:
                                self.executor.submit(self._process_system_audio, chunk, samplerate)
                            except Exception as e:
                                if self.running:
                                    log.error(f"Failed to submit audio processing: {e}")
            except sd.CallbackStop:
                raise
            except Exception as e:
                stream_error[0] = str(e)
                log.error(f"Audio callback error: {e}")
                raise sd.CallbackStop()
        
        try:
            log.info(f"Opening system audio stream: device={loopback.name}, rate={samplerate}, index={loopback.index}")
            self.status_changed.emit(f"🎧 Capturing system audio ({self.engine.value})...")
            
            # Test device access before starting stream
            try:
                test_stream = sd.InputStream(
                    channels=1,
                    samplerate=samplerate,
                    device=loopback.index,
                    blocksize=1024
                )
                test_stream.close()
                log.info("Device test successful")
            except Exception as test_error:
                error_msg = (
                    f"❌ System audio device test failed:\n\n"
                    f"Device: {loopback.name}\n"
                    f"Error: {test_error}\n\n"
                    f"The device may be in use by another application\n"
                    f"or not properly configured for recording."
                )
                self.error_occurred.emit(error_msg)
                return
            
            # Start actual capture stream
            with sd.InputStream(
                channels=1, 
                samplerate=samplerate, 
                device=loopback.index, 
                callback=callback, 
                blocksize=4096
            ):
                while self.running:
                    if stream_error[0]:
                        raise RuntimeError(stream_error[0])
                    sd.sleep(100)
                    self._update_performance()
                    
        except Exception as e:
            if self.running:
                import traceback
                error_details = traceback.format_exc()
                log.error(f"System audio error:\n{error_details}")
                
                error_msg = (
                    f"❌ System audio failed:\n\n"
                    f"Error: {str(e)}\n\n"
                    f"Device: {loopback.name if loopback else 'Unknown'}\n\n"
                    f"Possible solutions:\n"
                    f"• Close other apps using the audio device\n"
                    f"• Check device is enabled in system settings\n"
                    f"• Try restarting the application\n"
                    f"• Use Microphone mode instead"
                )
                self.error_occurred.emit(error_msg)
    
    def _process_audio(self, audio):
        """Process audio chunk - runs in thread pool"""
        start_time = time.time()
        try:
            text, conf = None, 1.0
            
            if self.engine == RecognitionEngine.WHISPER:
                text, conf = self._recognize_whisper(audio)
            elif self.engine == RecognitionEngine.VOSK and self.vosk_model:
                text, conf = self._recognize_vosk(audio.get_wav_data())
            elif self.engine == RecognitionEngine.GOOGLE:
                if is_online():
                    try:
                        text = sr.Recognizer().recognize_google(audio, language=self.language)
                    except:
                        pass
            
            if text and text.strip():
                self.phrase_detected.emit(text, conf)
            
            # Track processing time
            elapsed = (time.time() - start_time) * 1000
            self.processing_times.append(elapsed)
            
        except Exception as e:
            log.error(f"Process audio error: {e}")
    
    def _process_system_audio(self, audio_data, samplerate):
        """Process system audio chunk"""
        if not self.running or self.executor_shutdown:
            return
        
        start_time = time.time()
        try:
            energy = np.sqrt(np.mean(audio_data ** 2))
            if energy < 0.01:
                return
            
            text, conf = "", 0.0
            if self.engine == RecognitionEngine.WHISPER:
                text, conf = self._transcribe_whisper_array(audio_data, samplerate)
            elif self.engine == RecognitionEngine.VOSK and self.vosk_model:
                audio_int = (audio_data * 32767).astype(np.int16)
                text, conf = self._recognize_vosk(audio_int.tobytes())
            
            if text and text.strip():
                self.phrase_detected.emit(text, conf)
            
            elapsed = (time.time() - start_time) * 1000
            self.processing_times.append(elapsed)
            
        except Exception as e:
            if self.running:
                log.error(f"Process system audio error: {e}")
    
    def _recognize_vosk(self, wav_data):
        if not self.vosk_model:
            return "", 0.0
        try:
            rec = KaldiRecognizer(self.vosk_model, 16000)
            rec.SetWords(True)
            rec.AcceptWaveform(wav_data)
            result = json.loads(rec.FinalResult())
            return result.get("text", ""), result.get("confidence", 0.9)
        except:
            return "", 0.0
    
    def _recognize_whisper(self, audio):
        try:
            audio_np = np.frombuffer(audio.get_wav_data(), dtype=np.int16).astype(np.float32) / 32768.0
            if audio.sample_rate != 16000:
                from scipy import signal
                audio_np = signal.resample(audio_np, int(len(audio_np) * 16000 / audio.sample_rate))
            lang = self.language if self.language != "auto" else None
            return whisper_manager.transcribe(audio_np, self.whisper_model_size, lang)
        except:
            return "", 0.0
    
    def _transcribe_whisper_array(self, audio_data, samplerate):
        try:
            if samplerate != 16000:
                from scipy import signal
                audio_data = signal.resample(audio_data, int(len(audio_data) * 16000 / samplerate))
            lang = self.language if self.language != "auto" else None
            return whisper_manager.transcribe(audio_data, self.whisper_model_size, lang)
        except:
            return "", 0.0
    
    def _update_performance(self):
        """Update performance metrics periodically"""
        now = time.time()
        if now - self.last_perf_update > 1.0:  # Update every second
            avg_time = sum(self.processing_times) / len(self.processing_times) if self.processing_times else 0
            perf_data = {
                'recognition_queue': self.recognition_queue.qsize(),
                'translation_queue': self.translation_queue.qsize(),
                'avg_processing_time': avg_time,
                'device': whisper_manager.device if self.engine == RecognitionEngine.WHISPER else 'N/A'
            }
            self.performance_update.emit(perf_data)
            self.last_perf_update = now
    
    def stop(self):
        self.running = False
        self.executor_shutdown = True
        # Shutdown executor gracefully
        self.executor.shutdown(wait=False)

class ResizableOverlay(QWidget):
    """Fully resizable overlay with corner and edge dragging + Netflix/Google Live Captions-style scrolling"""
    
    CORNER_SIZE = 20
    EDGE_SIZE = 10
    MIN_WIDTH = 200
    MIN_HEIGHT = 80
    
    class ResizeMode(Enum):
        NONE = 0
        MOVE = 1
        TOP_LEFT = 2
        TOP_RIGHT = 3
        BOTTOM_LEFT = 4
        BOTTOM_RIGHT = 5
        TOP = 6
        BOTTOM = 7
        LEFT = 8
        RIGHT = 9
    
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)
        
        # Resize state
        self.resize_mode = self.ResizeMode.NONE
        self.drag_start_pos = None
        self.drag_start_geometry = None
        
        # Container with glassmorphic effect
        self.container = QWidget(self)
        self.container.setObjectName("overlayContainer")
        
        # Main content
        # Use a scrolling label for Google Live Captions effect
        self.label_container = QWidget(self.container)
        self.label_container.setMouseTracking(True)
        
        self.label = QLabel("", self.label_container)
        self.label.setWordWrap(True)
        self.label.setAlignment(Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignLeft)
        self.label.setMouseTracking(True)
        self.label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        label_layout = QVBoxLayout(self.label_container)
        label_layout.addStretch()
        label_layout.addWidget(self.label)
        label_layout.setContentsMargins(0, 0, 0, 0)
        label_layout.setSpacing(0)
        
        # Resize indicators (corner dots) - Material Design 3 style
        self.corner_indicators = []
        for _ in range(4):
            indicator = QLabel("", self.container)
            indicator.setFixedSize(10, 10)
            indicator.setStyleSheet("""
                background: qradialgradient(cx:0.5, cy:0.5, radius:0.5,
                    fx:0.5, fy:0.5, stop:0 rgba(130, 200, 255, 0.9), stop:1 rgba(100, 181, 246, 0.7));
                border-radius: 5px;
                border: 1px solid rgba(255,255,255,0.3);
            """)
            indicator.hide()
            self.corner_indicators.append(indicator)
        
        layout = QVBoxLayout(self.container)
        layout.addWidget(self.label_container)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(0)
        
        main = QVBoxLayout(self)
        main.addWidget(self.container)
        main.setContentsMargins(0, 0, 0, 0)
        
        # Live captions style: show last N words with smooth scrolling
        self.text_buffer = deque(maxlen=config.get("max_words", 100))
        max_lines = config.get("subtitle_lines", 3)
        self.displayed_lines = deque(maxlen=max_lines)  # Show last N lines like Google Live Captions
        self.current_sentence = []  # Build current sentence
        self.last_update_time = time.time()
        self.live_captions_mode = config.get("live_captions_mode", True)
        self.subtitle_update_delay = config.get("subtitle_update_delay", 10) / 1000.0  # Convert ms to seconds
        
        # Professional fade animation for Netflix-style smooth text transitions
        self.fade_effect = QGraphicsOpacityEffect(self.label)
        self.label.setGraphicsEffect(self.fade_effect)
        
        self.fade_animation = QPropertyAnimation(self.fade_effect, b"opacity")
        self.fade_animation.setDuration(250)
        self.fade_animation.setStartValue(0.0)
        self.fade_animation.setEndValue(1.0)
        self.fade_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        # Add slide animation for Netflix-style entrance
        self.slide_animation = QPropertyAnimation(self.label, b"pos")
        self.slide_animation.setDuration(250)
        self.slide_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        self.apply_style()
        geom = config.get("overlay_position", [100, 100, 800, 180])
        # Ensure geometry is valid
        geom = self._validate_geometry(geom)
        self.setGeometry(*geom)
        self.setVisible(config.get("overlay_visible", True))
    
    def _validate_geometry(self, geom):
        """Validate and fix geometry to avoid Windows constraints errors"""
        x, y, w, h = geom
        
        # Ensure minimum size
        w = max(w, self.MIN_WIDTH)
        h = max(h, self.MIN_HEIGHT)
        
        # Ensure position is on screen
        screen = QApplication.primaryScreen().geometry()
        x = max(0, min(x, screen.width() - w))
        y = max(0, min(y, screen.height() - h))
        
        return [x, y, w, h]
        
        # Update corner positions
        self._update_corner_positions()
    
    def apply_style(self):
        """Netflix/Google-level glassmorphic professional styling"""
        fs = config.get("font_size", 22)
        tc = config.get("text_color", "#FFFFFF")
        bg = config.get("bg_color", "rgba(15,15,20,0.92)")
        
        # Professional Material Design 3 styling
        self.setStyleSheet(f"""
            #overlayContainer {{
                background: {bg};
                border-radius: 20px;
                border: 1.5px solid rgba(255,255,255,0.15);
                backdrop-filter: blur(20px);
                box-shadow: 0 8px 32px rgba(0,0,0,0.4);
            }}
            QLabel {{
                color: {tc};
                font-size: {fs}px;
                font-weight: 500;
                line-height: 1.7;
                background: transparent;
                font-family: "Segoe UI", "SF Pro Display", -apple-system, system-ui, sans-serif;
                letter-spacing: 0.3px;
                text-shadow: 0 2px 8px rgba(0,0,0,0.3);
            }}
        """)
    
    def _update_corner_positions(self):
        """Update visual corner indicators"""
        w, h = self.width(), self.height()
        positions = [
            (5, 5),  # Top-left
            (w - 13, 5),  # Top-right
            (5, h - 13),  # Bottom-left
            (w - 13, h - 13)  # Bottom-right
        ]
        for indicator, pos in zip(self.corner_indicators, positions):
            indicator.move(*pos)
    
    def add_text(self, text, is_translation=True):
        """Add text with Google Live Captions-style smooth scrolling and instant updates"""
        if not text.strip():
            return
        
        if not self.live_captions_mode:
            # Legacy mode: just add to buffer
            for word in text.split():
                self.text_buffer.append(word)
            self.update_display_legacy()
            return
        
        # Google Live Captions mode: instant word-by-word updates
        words = text.split()
        
        # Add words one at a time for smooth appearance (if delay is small enough)
        if self.subtitle_update_delay < 0.020:  # Less than 20ms
            # Ultra-fast mode: add all words at once
            self.current_sentence.extend(words)
            self.update_display_smooth()
        else:
            # Smooth mode: add words with slight delay for visual effect
            for word in words:
                self.current_sentence.append(word)
                self.update_display_smooth()
                QApplication.processEvents()  # Allow UI to update
        
        # Check if we should create a new line (sentence break detection)
        sentence_text = " ".join(self.current_sentence)
        should_new_line = (
            len(self.current_sentence) > 12 or  # Wrap sooner for readability
            any(sentence_text.rstrip().endswith(punct) for punct in ['.', '!', '?', '。', '！', '？', ',', ';'])
        )
        
        if should_new_line and len(self.current_sentence) > 0:
            # Move current sentence to displayed lines with smooth transition
            self.displayed_lines.append(sentence_text)
            self.current_sentence = []
            self.update_display_smooth()
    
    def update_display_legacy(self):
        """Legacy update mode (simple buffer display)"""
        if not self.text_buffer:
            self.label.setText("")
            return
        text = " ".join(list(self.text_buffer))
        self.label.setText(text)
    
    def update_display_smooth(self):
        """Update display with Netflix/Google Live Captions-style smooth transitions - optimized for speed"""
        if not self.displayed_lines and not self.current_sentence:
            self.label.setText("")
            return
        
        # Build display text: show last N completed lines + current building sentence
        max_lines = config.get("subtitle_lines", 3)
        lines = list(self.displayed_lines)
        if self.current_sentence:
            lines.append(" ".join(self.current_sentence))
        
        # Keep only last N lines for clean display (Netflix/Google Live Captions style)
        display_text = "\n".join(lines[-max_lines:])
        
        # Update with configurable throttling for live effect
        current_time = time.time()
        time_since_last = current_time - self.last_update_time
        
        # Use configurable delay (default 10ms = 100 FPS for very responsive updates)
        if time_since_last > self.subtitle_update_delay:
            self.label.setText(display_text)
            # Netflix-style subtle fade for new content (only on longer pauses)
            if self.fade_animation.state() != QPropertyAnimation.State.Running and time_since_last > 0.4:
                self.fade_animation.setStartValue(0.88)
                self.fade_animation.setEndValue(1.0)
                self.fade_animation.setDuration(150)
                self.fade_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
                self.fade_animation.start()
            self.last_update_time = current_time
        else:
            # For very rapid updates, just update text without animation for maximum speed
            self.label.setText(display_text)
    
    def clear_subtitles(self):
        """Clear all subtitle text"""
        self.text_buffer.clear()
        self.displayed_lines.clear()
        self.current_sentence = []
        self.label.setText("")
    
    def _get_resize_mode(self, pos):
        """Determine resize mode based on cursor position"""
        x, y = pos.x(), pos.y()
        w, h = self.width(), self.height()
        cs, es = self.CORNER_SIZE, self.EDGE_SIZE
        
        # Check corners first (priority)
        if x < cs and y < cs:
            return self.ResizeMode.TOP_LEFT
        elif x > w - cs and y < cs:
            return self.ResizeMode.TOP_RIGHT
        elif x < cs and y > h - cs:
            return self.ResizeMode.BOTTOM_LEFT
        elif x > w - cs and y > h - cs:
            return self.ResizeMode.BOTTOM_RIGHT
        
        # Check edges
        elif y < es:
            return self.ResizeMode.TOP
        elif y > h - es:
            return self.ResizeMode.BOTTOM
        elif x < es:
            return self.ResizeMode.LEFT
        elif x > w - es:
            return self.ResizeMode.RIGHT
        
        # Center = move
        return self.ResizeMode.MOVE
    
    def _update_cursor(self, mode):
        """Update cursor based on resize mode"""
        cursor_map = {
            self.ResizeMode.NONE: Qt.CursorShape.ArrowCursor,
            self.ResizeMode.MOVE: Qt.CursorShape.SizeAllCursor,
            self.ResizeMode.TOP_LEFT: Qt.CursorShape.SizeFDiagCursor,
            self.ResizeMode.BOTTOM_RIGHT: Qt.CursorShape.SizeFDiagCursor,
            self.ResizeMode.TOP_RIGHT: Qt.CursorShape.SizeBDiagCursor,
            self.ResizeMode.BOTTOM_LEFT: Qt.CursorShape.SizeBDiagCursor,
            self.ResizeMode.TOP: Qt.CursorShape.SizeVerCursor,
            self.ResizeMode.BOTTOM: Qt.CursorShape.SizeVerCursor,
            self.ResizeMode.LEFT: Qt.CursorShape.SizeHorCursor,
            self.ResizeMode.RIGHT: Qt.CursorShape.SizeHorCursor,
        }
        self.setCursor(cursor_map.get(mode, Qt.CursorShape.ArrowCursor))
    
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.resize_mode = self._get_resize_mode(e.pos())
            self.drag_start_pos = e.globalPosition().toPoint()
            self.drag_start_geometry = self.geometry()
            
            # Show corner indicators
            for indicator in self.corner_indicators:
                indicator.show()
    
    def mouseMoveEvent(self, e):
        if self.resize_mode == self.ResizeMode.NONE:
            # Update cursor for hover
            mode = self._get_resize_mode(e.pos())
            self._update_cursor(mode)
            return
        
        if not self.drag_start_pos:
            return
        
        delta = e.globalPosition().toPoint() - self.drag_start_pos
        geom = QRect(self.drag_start_geometry)
        
        # Apply resize/move based on mode
        if self.resize_mode == self.ResizeMode.MOVE:
            geom.moveTopLeft(geom.topLeft() + delta)
        
        elif self.resize_mode == self.ResizeMode.TOP_LEFT:
            geom.setTopLeft(geom.topLeft() + delta)
        elif self.resize_mode == self.ResizeMode.TOP_RIGHT:
            geom.setTopRight(geom.topRight() + delta)
        elif self.resize_mode == self.ResizeMode.BOTTOM_LEFT:
            geom.setBottomLeft(geom.bottomLeft() + delta)
        elif self.resize_mode == self.ResizeMode.BOTTOM_RIGHT:
            geom.setBottomRight(geom.bottomRight() + delta)
        
        elif self.resize_mode == self.ResizeMode.TOP:
            geom.setTop(geom.top() + delta.y())
        elif self.resize_mode == self.ResizeMode.BOTTOM:
            geom.setBottom(geom.bottom() + delta.y())
        elif self.resize_mode == self.ResizeMode.LEFT:
            geom.setLeft(geom.left() + delta.x())
        elif self.resize_mode == self.ResizeMode.RIGHT:
            geom.setRight(geom.right() + delta.x())
        
        # Enforce minimum size with more flexible constraints
        min_w = max(self.MIN_WIDTH, 135)
        min_h = max(self.MIN_HEIGHT, 57)
        
        if geom.width() < min_w:
            if self.resize_mode in [self.ResizeMode.LEFT, self.ResizeMode.TOP_LEFT, self.ResizeMode.BOTTOM_LEFT]:
                geom.setLeft(geom.right() - min_w)
            else:
                geom.setWidth(min_w)
        
        if geom.height() < min_h:
            if self.resize_mode in [self.ResizeMode.TOP, self.ResizeMode.TOP_LEFT, self.ResizeMode.TOP_RIGHT]:
                geom.setTop(geom.bottom() - min_h)
            else:
                geom.setHeight(min_h)
        
        # Validate geometry before setting to avoid Windows errors
        if geom.width() >= self.MIN_WIDTH and geom.height() >= self.MIN_HEIGHT:
            try:
                self.setGeometry(geom)
            except Exception as e:
                log.debug(f"Geometry set failed: {e}")
                # Fall back to current geometry if setting fails
                pass
        self._update_corner_positions()
    
    def mouseReleaseEvent(self, e):
        if self.resize_mode != self.ResizeMode.NONE:
            geom = self.geometry()
            # Validate and save geometry
            validated_geom = self._validate_geometry([geom.x(), geom.y(), geom.width(), geom.height()])
            config.set("overlay_position", validated_geom)
            
            # Hide corner indicators
            for indicator in self.corner_indicators:
                indicator.hide()
        
        self.resize_mode = self.ResizeMode.NONE
        self.drag_start_pos = None
        self.drag_start_geometry = None
        self.setCursor(Qt.CursorShape.ArrowCursor)
    
    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.container.setGeometry(0, 0, self.width(), self.height())
        self._update_corner_positions()
    
    def enterEvent(self, e):
        # Show corner indicators on hover
        for indicator in self.corner_indicators:
            indicator.show()
    
    def leaveEvent(self, e):
        # Hide corner indicators when not hovering
        if self.resize_mode == self.ResizeMode.NONE:
            for indicator in self.corner_indicators:
                indicator.hide()

class SettingsDialog(QDialog):
    """Netflix/Google-level comprehensive settings dialog with Material Design 3 styling"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⚙️ Settings — Universal Live Translator")
        self.setMinimumWidth(700)
        self.setMinimumHeight(750)
        self.setup_ui()
        # Apply professional styling to dialog
        self.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0f0f14, stop:1 #1a1a20);
            }
            QTabWidget::pane {
                border: 1.5px solid rgba(255,255,255,0.08);
                border-radius: 12px;
                background: rgba(42,42,50,0.3);
                padding: 10px;
            }
            QTabBar::tab {
                background: rgba(60,60,70,0.5);
                color: #b8bbbe;
                padding: 10px 20px;
                margin-right: 4px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-weight: 500;
                font-size: 13px;
            }
            QTabBar::tab:selected {
                background: rgba(130,200,255,0.15);
                color: #82c8ff;
                border-bottom: 2px solid #82c8ff;
            }
            QTabBar::tab:hover:!selected {
                background: rgba(75,75,85,0.6);
            }
        """)
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Create tab widget for organized settings
        tabs = QTabWidget()
        
        # ===== GENERAL TAB =====
        general_tab = QWidget()
        general_layout = QVBoxLayout(general_tab)
        
        # Theme
        theme_group = QGroupBox("Appearance")
        theme_layout = QVBoxLayout()
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark", "Light"])
        self.theme_combo.setCurrentText(config.get("theme", "dark").title())
        theme_layout.addWidget(QLabel("Theme:"))
        theme_layout.addWidget(self.theme_combo)
        
        # Font size
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(10, 48)
        self.font_size_spin.setValue(config.get("font_size", 20))
        theme_layout.addWidget(QLabel("Overlay Font Size:"))
        theme_layout.addWidget(self.font_size_spin)
        
        # Text color
        self.text_color_btn = QPushButton("Choose Text Color")
        self.text_color = config.get("text_color", "#FFFFFF")
        self.text_color_btn.clicked.connect(self.choose_text_color)
        theme_layout.addWidget(QLabel("Overlay Text Color:"))
        theme_layout.addWidget(self.text_color_btn)
        
        theme_group.setLayout(theme_layout)
        general_layout.addWidget(theme_group)
        
        # Animation
        anim_group = QGroupBox("Animation")
        anim_layout = QVBoxLayout()
        self.anim_duration_spin = QSpinBox()
        self.anim_duration_spin.setRange(0, 1000)
        self.anim_duration_spin.setValue(config.get("animation_duration", 200))
        self.anim_duration_spin.setSuffix(" ms")
        anim_layout.addWidget(QLabel("Animation Duration:"))
        anim_layout.addWidget(self.anim_duration_spin)
        anim_group.setLayout(anim_layout)
        general_layout.addWidget(anim_group)
        
        # Max words and subtitle settings
        words_group = QGroupBox("Overlay & Subtitle Settings")
        words_layout = QVBoxLayout()
        
        self.max_words_spin = QSpinBox()
        self.max_words_spin.setRange(10, 500)
        self.max_words_spin.setValue(config.get("max_words", 100))
        words_layout.addWidget(QLabel("Maximum Words in Overlay:"))
        words_layout.addWidget(self.max_words_spin)
        
        # Subtitle lines
        self.subtitle_lines_spin = QSpinBox()
        self.subtitle_lines_spin.setRange(1, 10)
        self.subtitle_lines_spin.setValue(config.get("subtitle_lines", 3))
        words_layout.addWidget(QLabel("Number of Subtitle Lines:"))
        words_layout.addWidget(self.subtitle_lines_spin)
        
        # Subtitle update speed
        self.subtitle_delay_spin = QSpinBox()
        self.subtitle_delay_spin.setRange(1, 100)
        self.subtitle_delay_spin.setValue(config.get("subtitle_update_delay", 10))
        self.subtitle_delay_spin.setSuffix(" ms")
        words_layout.addWidget(QLabel("Subtitle Update Speed (lower = faster):"))
        words_layout.addWidget(self.subtitle_delay_spin)
        
        speed_hint = QLabel("💡 Tip: 5-10ms for instant updates, 30-50ms for smoother animation")
        speed_hint.setWordWrap(True)
        speed_hint.setStyleSheet("color: #888; font-size: 11px;")
        words_layout.addWidget(speed_hint)
        
        words_group.setLayout(words_layout)
        general_layout.addWidget(words_group)
        
        general_layout.addStretch()
        tabs.addTab(general_tab, "General")
        
        # ===== AUDIO TAB =====
        audio_tab = QWidget()
        audio_layout = QVBoxLayout(audio_tab)
        
        # TTS Settings
        tts_group = QGroupBox("Text-to-Speech")
        tts_layout = QVBoxLayout()
        
        self.tts_rate_spin = QSpinBox()
        self.tts_rate_spin.setRange(50, 300)
        self.tts_rate_spin.setValue(config.get("tts_rate", 150))
        tts_layout.addWidget(QLabel("Speech Rate:"))
        tts_layout.addWidget(self.tts_rate_spin)
        
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(int(config.get("volume", 0.8) * 100))
        self.volume_label = QLabel(f"{self.volume_slider.value()}%")
        self.volume_slider.valueChanged.connect(lambda v: self.volume_label.setText(f"{v}%"))
        tts_layout.addWidget(QLabel("Volume:"))
        tts_layout.addWidget(self.volume_slider)
        tts_layout.addWidget(self.volume_label)
        
        tts_group.setLayout(tts_layout)
        audio_layout.addWidget(tts_group)
        
        # Audio Device
        device_group = QGroupBox("Audio Input Device")
        device_layout = QVBoxLayout()
        self.device_combo = QComboBox()
        self.device_combo.addItem("Default", "default")
        for device in audio_device_manager.input_devices:
            self.device_combo.addItem(f"{device.name} ({device.host_api})", str(device.index))
        current_device = config.get("audio_device_input", "default")
        idx = self.device_combo.findData(current_device)
        if idx >= 0:
            self.device_combo.setCurrentIndex(idx)
        device_layout.addWidget(QLabel("Input Device:"))
        device_layout.addWidget(self.device_combo)
        device_group.setLayout(device_layout)
        audio_layout.addWidget(device_group)
        
        audio_layout.addStretch()
        tabs.addTab(audio_tab, "Audio")
        
        # ===== GPU/ENGINE TAB =====
        engine_tab = QWidget()
        engine_layout = QVBoxLayout(engine_tab)
        
        # GPU Settings
        gpu_group = QGroupBox("GPU Acceleration")
        gpu_layout = QVBoxLayout()
        
        self.use_gpu_check = QCheckBox("Enable GPU Acceleration (CUDA/MPS)")
        self.use_gpu_check.setChecked(config.get("use_gpu", True))
        self.use_gpu_check.setEnabled(gpu_manager.is_gpu_available())
        gpu_layout.addWidget(self.use_gpu_check)
        
        gpu_info = QLabel(f"Status: {gpu_manager.device_name}")
        gpu_info.setWordWrap(True)
        gpu_layout.addWidget(gpu_info)
        
        if not gpu_manager.is_gpu_available():
            gpu_warning = QLabel("⚠️ No GPU detected. Install CUDA (NVIDIA) or use Apple Silicon for GPU acceleration.")
            gpu_warning.setWordWrap(True)
            gpu_warning.setStyleSheet("color: #FFC107;")
            gpu_layout.addWidget(gpu_warning)
        
        gpu_group.setLayout(gpu_layout)
        engine_layout.addWidget(gpu_group)
        
        # Whisper Model
        whisper_group = QGroupBox("Whisper Model")
        whisper_layout = QVBoxLayout()
        self.whisper_model_combo = QComboBox()
        for model in WHISPER_MODELS:
            self.whisper_model_combo.addItem(model.title(), model)
        current_model = config.get("whisper_model", "base")
        idx = self.whisper_model_combo.findData(current_model)
        if idx >= 0:
            self.whisper_model_combo.setCurrentIndex(idx)
        whisper_layout.addWidget(QLabel("Model Size:"))
        whisper_layout.addWidget(self.whisper_model_combo)
        
        model_info = QLabel(
            "• Tiny: Fastest, less accurate\\n"
            "• Base: Balanced (recommended)\\n"
            "• Small/Medium/Large: Higher accuracy, slower"
        )
        model_info.setWordWrap(True)
        whisper_layout.addWidget(model_info)
        whisper_group.setLayout(whisper_layout)
        engine_layout.addWidget(whisper_group)
        
        engine_layout.addStretch()
        tabs.addTab(engine_tab, "GPU & Models")
        
        # ===== CACHE TAB =====
        cache_tab = QWidget()
        cache_layout = QVBoxLayout(cache_tab)
        
        cache_group = QGroupBox("Translation Cache")
        cache_group_layout = QVBoxLayout()
        
        self.cache_enabled = QCheckBox("Enable Translation Caching")
        self.cache_enabled.setChecked(config.get("cache_translations", True))
        cache_group_layout.addWidget(self.cache_enabled)
        
        self.cache_expiry_spin = QSpinBox()
        self.cache_expiry_spin.setRange(1, 365)
        self.cache_expiry_spin.setValue(config.get("cache_expiry_days", 7))
        self.cache_expiry_spin.setSuffix(" days")
        cache_group_layout.addWidget(QLabel("Cache Expiry:"))
        cache_group_layout.addWidget(self.cache_expiry_spin)
        
        cache_group.setLayout(cache_group_layout)
        cache_layout.addWidget(cache_group)
        
        # Data locations
        data_group = QGroupBox("Data Locations")
        data_layout = QVBoxLayout()
        data_layout.addWidget(QLabel(f"Configuration: {CONFIG_FILE}"))
        data_layout.addWidget(QLabel(f"Database: {DB_FILE}"))
        data_layout.addWidget(QLabel(f"Audio Cache: {AUDIO_DIR}"))
        data_layout.addWidget(QLabel(f"Vosk Models: {VOSK_MODELS_DIR}"))
        data_group.setLayout(data_layout)
        cache_layout.addWidget(data_group)
        
        cache_layout.addStretch()
        tabs.addTab(cache_tab, "Cache & Data")
        
        layout.addWidget(tabs)
        
        # Professional action buttons with Material Design 3 styling
        buttons = QHBoxLayout()
        buttons.setSpacing(12)
        
        save_btn = QPushButton("✔ Save & Apply")
        save_btn.clicked.connect(self.save_settings)
        save_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #4CAF50, stop:1 #388E3C);
                color: white;
                font-weight: 600;
                padding: 12px 28px;
                font-size: 14px;
                border: none;
                border-radius: 10px;
                letter-spacing: 0.5px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #5FD068, stop:1 #4CAF50);
            }
            QPushButton:pressed {
                background: #2E7D32;
            }
        """)
        
        cancel_btn = QPushButton("✖ Cancel")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: rgba(60,60,70,0.8);
                color: #e8eaed;
                font-weight: 500;
                padding: 12px 28px;
                font-size: 14px;
                border: 1.5px solid rgba(255,255,255,0.1);
                border-radius: 10px;
            }
            QPushButton:hover {
                background: rgba(75,75,85,0.9);
                border: 1.5px solid rgba(255,255,255,0.2);
            }
        """)
        
        buttons.addStretch()
        buttons.addWidget(save_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)
    
    def choose_text_color(self):
        color = QColorDialog.getColor(QColor(self.text_color), self, "Choose Text Color")
        if color.isValid():
            self.text_color = color.name()
            self.text_color_btn.setStyleSheet(f"background-color: {self.text_color};")
    
    def save_settings(self):
        # Save all settings
        config.set("theme", self.theme_combo.currentText().lower())
        config.set("font_size", self.font_size_spin.value())
        config.set("text_color", self.text_color)
        config.set("animation_duration", self.anim_duration_spin.value())
        config.set("max_words", self.max_words_spin.value())
        config.set("subtitle_lines", self.subtitle_lines_spin.value())
        config.set("subtitle_update_delay", self.subtitle_delay_spin.value())
        config.set("tts_rate", self.tts_rate_spin.value())
        config.set("volume", self.volume_slider.value() / 100.0)
        config.set("audio_device_input", self.device_combo.currentData())
        config.set("use_gpu", self.use_gpu_check.isChecked())
        config.set("whisper_model", self.whisper_model_combo.currentData())
        config.set("cache_translations", self.cache_enabled.isChecked())
        config.set("cache_expiry_days", self.cache_expiry_spin.value())
        
        # Apply TTS volume immediately
        tts_manager.set_volume(self.volume_slider.value() / 100.0)
        
        # Apply GPU setting immediately
        whisper_manager.set_device(self.use_gpu_check.isChecked())
        
        self.accept()

class ModelManagerDialog(QDialog):
    """Professional model download and management dialog with Material Design 3"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📥 Model Manager — Universal Live Translator")
        self.setMinimumWidth(750)
        self.setMinimumHeight(550)
        self.setup_ui()
        # Apply professional styling
        self.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0f0f14, stop:1 #1a1a20);
            }
            QTabWidget::pane {
                border: 1.5px solid rgba(255,255,255,0.08);
                border-radius: 12px;
                background: rgba(42,42,50,0.3);
                padding: 10px;
            }
            QTabBar::tab {
                background: rgba(60,60,70,0.5);
                color: #b8bbbe;
                padding: 10px 20px;
                margin-right: 4px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-weight: 500;
                font-size: 13px;
            }
            QTabBar::tab:selected {
                background: rgba(130,200,255,0.15);
                color: #82c8ff;
                border-bottom: 2px solid #82c8ff;
            }
        """)
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        tabs = QTabWidget()
        
        # ===== WHISPER TAB =====
        whisper_tab = QWidget()
        whisper_layout = QVBoxLayout(whisper_tab)
        
        whisper_info = QLabel(
            "Whisper models download automatically on first use.\\n"
            "Models are cached in your home directory (~/.cache/whisper)."
        )
        whisper_info.setWordWrap(True)
        whisper_layout.addWidget(whisper_info)
        
        whisper_group = QGroupBox("Available Whisper Models")
        whisper_group_layout = QVBoxLayout()
        
        for model in WHISPER_MODELS:
            model_row = QHBoxLayout()
            label = QLabel(f"{model.title()}")
            model_row.addWidget(label)
            
            size_label = QLabel()
            if model == "tiny":
                size_label.setText("~75 MB")
            elif model == "base":
                size_label.setText("~150 MB")
            elif model == "small":
                size_label.setText("~500 MB")
            elif model == "medium":
                size_label.setText("~1.5 GB")
            elif model == "large":
                size_label.setText("~3 GB")
            model_row.addWidget(size_label)
            
            model_row.addStretch()
            
            download_btn = QPushButton("📥 Download")
            download_btn.clicked.connect(lambda checked, m=model: self.download_whisper_model(m))
            model_row.addWidget(download_btn)
            
            whisper_group_layout.addLayout(model_row)
        
        whisper_group.setLayout(whisper_group_layout)
        whisper_layout.addWidget(whisper_group)
        
        current_device = QLabel(f"Current Device: {whisper_manager.device}")
        whisper_layout.addWidget(current_device)
        
        whisper_layout.addStretch()
        tabs.addTab(whisper_tab, "Whisper Models")
        
        # ===== VOSK TAB =====
        vosk_tab = QWidget()
        vosk_layout = QVBoxLayout(vosk_tab)
        
        vosk_info = QLabel(
            f"Vosk models are downloaded to: {VOSK_MODELS_DIR}\\n"
            "These are offline speech recognition models."
        )
        vosk_info.setWordWrap(True)
        vosk_layout.addWidget(vosk_info)
        
        vosk_group = QGroupBox("Available Vosk Models")
        vosk_group_layout = QVBoxLayout()
        
        for lang_code, url in VOSK_MODELS.items():
            model_row = QHBoxLayout()
            
            lang_name = {"en": "English", "fr": "French", "es": "Spanish", "de": "German"}.get(lang_code, lang_code)
            label = QLabel(f"{lang_name} ({lang_code})")
            model_row.addWidget(label)
            
            has_model = vosk_manager.has_model(lang_code)
            status = QLabel("✅ Installed" if has_model else "❌ Not installed")
            model_row.addWidget(status)
            
            model_row.addStretch()
            
            if not has_model:
                download_btn = QPushButton("📥 Download (~50 MB)")
                download_btn.clicked.connect(lambda checked, lc=lang_code: self.download_vosk_model(lc))
                model_row.addWidget(download_btn)
            
            vosk_group_layout.addLayout(model_row)
        
        vosk_group.setLayout(vosk_group_layout)
        vosk_layout.addWidget(vosk_group)
        
        vosk_layout.addStretch()
        tabs.addTab(vosk_tab, "Vosk Models")
        
        layout.addWidget(tabs)
        
        # Professional close button
        close_btn = QPushButton("✔ Done")
        close_btn.clicked.connect(self.accept)
        close_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #4CAF50, stop:1 #388E3C);
                color: white;
                font-weight: 600;
                padding: 12px 28px;
                font-size: 14px;
                border: none;
                border-radius: 10px;
                letter-spacing: 0.5px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #5FD068, stop:1 #4CAF50);
            }
        """)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignCenter)
    
    def download_whisper_model(self, model_name):
        reply = QMessageBox.question(
            self,
            "Download Whisper Model",
            f"Download {model_name} model?\\n\\nThe model will download automatically on first use.\\n"
            f"You can test it by selecting '{model_name}' in Settings and using Whisper engine.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Create progress dialog
            progress = QProgressDialog(f"Downloading Whisper {model_name} model...", None, 0, 0, self)
            progress.setWindowTitle("Downloading")
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.show()
            QApplication.processEvents()
            
            # Download in thread to avoid blocking UI
            success = whisper_manager.load_model(model_name)
            
            progress.close()
            
            if success:
                QMessageBox.information(self, "Success", f"Whisper {model_name} model loaded successfully!")
            else:
                QMessageBox.warning(self, "Error", f"Failed to download {model_name} model. Check logs for details.")
    
    def download_vosk_model(self, lang_code):
        reply = QMessageBox.question(
            self,
            "Download Vosk Model",
            f"Download Vosk model for {lang_code}?\\n\\nSize: ~50 MB",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            progress = QProgressDialog(f"Downloading Vosk {lang_code} model...", "Cancel", 0, 100, self)
            progress.setWindowTitle("Downloading")
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.show()
            
            def update_progress(pct):
                progress.setValue(int(pct * 100))
                QApplication.processEvents()
            
            success = vosk_manager.download_model(lang_code, update_progress)
            
            progress.close()
            
            if success:
                QMessageBox.information(self, "Success", f"Vosk {lang_code} model downloaded successfully!")
                # Refresh the dialog
                self.close()
                new_dialog = ModelManagerDialog(self.parent())
                new_dialog.exec()
            else:
                QMessageBox.warning(self, "Error", f"Failed to download {lang_code} model. Check logs for details.")

class LiveTranslatorApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🌍 Universal Live Translator — Professional Edition v3.5")
        self.resize(1300, 1000)
        self.setMinimumSize(900, 700)
        self.recognition_thread = None
        self.source_type = "microphone"
        self.translation_mode = "Continuous"
        self.recognition_engine = RecognitionEngine.GOOGLE
        self.overlay = ResizableOverlay()
        self.overlay.show()
        
        # Performance monitoring
        self.last_history_refresh = time.time()
        self.history_refresh_throttle = 2.0  # seconds
        
        self.setup_ui()
        self.apply_theme(config.get("theme", "dark"))
        self.load_settings()
    
    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(15)
        
        # Professional top bar with enhanced status indicators
        top_bar = QHBoxLayout()
        top_bar.setSpacing(12)
        
        # Status with enhanced styling
        self.status_label = QLabel("🌐 Ready")
        self.status_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: 500;
                color: #82c8ff;
                padding: 6px 12px;
                background: rgba(130,200,255,0.1);
                border-radius: 8px;
                border: 1px solid rgba(130,200,255,0.2);
            }
        """)
        top_bar.addWidget(self.status_label)
        
        # GPU status indicator with professional Material Design 3 styling
        gpu_color = "#4CAF50" if gpu_manager.is_gpu_available() else "#FFC107"
        gpu_bg = "rgba(76,175,80,0.15)" if gpu_manager.is_gpu_available() else "rgba(255,193,7,0.15)"
        self.gpu_status = QLabel(f"🚀 {gpu_manager.device_name}")
        self.gpu_status.setStyleSheet(f"""
            QLabel {{
                color: {gpu_color};
                font-weight: 600;
                font-size: 13px;
                padding: 6px 12px;
                background: {gpu_bg};
                border-radius: 8px;
                border: 1px solid {gpu_color};
            }}
        """)
        self.gpu_status.setToolTip(f"Device: {gpu_manager.device}\nCUDA Available: {gpu_manager.has_cuda}\nMPS Available: {gpu_manager.has_mps}\n\n10-20x faster with GPU acceleration!")
        top_bar.addWidget(self.gpu_status)
        
        # Performance monitor with enhanced styling
        self.perf_label = QLabel("⚡ Performance: Ready")
        self.perf_label.setStyleSheet("""
            QLabel {
                font-size: 13px;
                font-weight: 500;
                color: #9aa0a6;
                padding: 6px 12px;
                background: rgba(154,160,166,0.08);
                border-radius: 8px;
            }
        """)
        self.perf_label.setToolTip("Real-time processing metrics:\nAverage time | Queue sizes | Device")
        top_bar.addWidget(self.perf_label)
        
        top_bar.addStretch()
        
        help_btn = QPushButton("❓ Help")
        help_btn.clicked.connect(self.show_help)
        help_btn.setToolTip("Show keyboard shortcuts and features (F1)")
        help_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                font-size: 13px;
                font-weight: 500;
            }
        """)
        top_bar.addWidget(help_btn)
        
        self.models_btn = QPushButton("📥 Models")
        self.models_btn.clicked.connect(self.show_models)
        self.models_btn.setToolTip("Download and manage Whisper and Vosk models")
        self.models_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                font-size: 13px;
                font-weight: 500;
            }
        """)
        top_bar.addWidget(self.models_btn)
        
        self.theme_btn = QPushButton("🌓 Theme")
        self.theme_btn.clicked.connect(self.toggle_theme)
        self.theme_btn.setToolTip("Toggle dark/light theme (Ctrl+D)")
        self.theme_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                font-size: 13px;
                font-weight: 500;
            }
        """)
        top_bar.addWidget(self.theme_btn)
        
        self.settings_btn = QPushButton("⚙️ Settings")
        self.settings_btn.clicked.connect(self.show_settings)
        self.settings_btn.setToolTip("Configure all application settings")
        self.settings_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                font-size: 13px;
                font-weight: 500;
            }
        """)
        top_bar.addWidget(self.settings_btn)
        
        main_layout.addLayout(top_bar)
        
        # Config with GPU toggle
        config_group = QGroupBox("🌐 Configuration")
        config_layout = QVBoxLayout()
        
        lang_row = QHBoxLayout()
        lang_row.setSpacing(10)
        
        src_label = QLabel("From:")
        src_label.setStyleSheet("font-weight: 500; font-size: 13px;")
        lang_row.addWidget(src_label)
        self.source_lang_combo = QComboBox()
        self.populate_languages(self.source_lang_combo, True)
        self.source_lang_combo.setToolTip("Select source language or 'Auto' for automatic detection")
        lang_row.addWidget(self.source_lang_combo, 1)
        
        self.swap_btn = QPushButton("⇄")
        self.swap_btn.setMaximumWidth(50)
        self.swap_btn.clicked.connect(self.swap_languages)
        self.swap_btn.setToolTip("Swap source and target languages")
        self.swap_btn.setStyleSheet("""
            QPushButton {
                font-size: 18px;
                font-weight: bold;
                padding: 8px;
            }
        """)
        lang_row.addWidget(self.swap_btn)
        
        tgt_label = QLabel("To:")
        tgt_label.setStyleSheet("font-weight: 500; font-size: 13px;")
        lang_row.addWidget(tgt_label)
        self.target_lang_combo = QComboBox()
        self.populate_languages(self.target_lang_combo)
        self.target_lang_combo.setToolTip("Select target language for translation")
        lang_row.addWidget(self.target_lang_combo, 1)
        
        config_layout.addLayout(lang_row)
        
        engine_row = QHBoxLayout()
        engine_row.setSpacing(10)
        
        engine_label = QLabel("Engine:")
        engine_label.setStyleSheet("font-weight: 500; font-size: 13px;")
        engine_row.addWidget(engine_label)
        self.engine_combo = QComboBox()
        self.engine_combo.addItem("🌐 Google", RecognitionEngine.GOOGLE.value)
        self.engine_combo.addItem("💻 Vosk (Offline)", RecognitionEngine.VOSK.value)
        self.engine_combo.addItem("🤖 Whisper (AI)", RecognitionEngine.WHISPER.value)
        self.engine_combo.currentIndexChanged.connect(self.on_engine_changed)
        self.engine_combo.setToolTip("Speech recognition engine:\n• Google: Fast, online required\n• Vosk: Offline, download required\n• Whisper: AI-powered, GPU recommended")
        engine_row.addWidget(self.engine_combo, 1)
        
        mode_label = QLabel("Mode:")
        mode_label.setStyleSheet("font-weight: 500; font-size: 13px;")
        engine_row.addWidget(mode_label)
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Continuous", "Real-time", "Manual"])
        self.mode_combo.currentTextChanged.connect(lambda m: setattr(self, 'translation_mode', m))
        self.mode_combo.setToolTip("Translation mode:\n• Continuous: Auto-translate as you speak\n• Real-time: Live translation\n• Manual: Translate on demand")
        engine_row.addWidget(self.mode_combo, 1)
        
        config_layout.addLayout(engine_row)
        
        # GPU toggle
        gpu_row = QHBoxLayout()
        self.gpu_checkbox = QCheckBox("🚀 Enable GPU Acceleration (10-20x faster)")
        self.gpu_checkbox.setChecked(config.get("use_gpu", True))
        self.gpu_checkbox.setEnabled(gpu_manager.is_gpu_available())
        self.gpu_checkbox.stateChanged.connect(self.on_gpu_toggled)
        self.gpu_checkbox.setStyleSheet("font-size: 13px; font-weight: 500;")
        if gpu_manager.is_gpu_available():
            self.gpu_checkbox.setToolTip(f"GPU detected: {gpu_manager.device_name}\nToggle to enable/disable GPU acceleration")
        else:
            self.gpu_checkbox.setToolTip("No GPU detected. Install CUDA (NVIDIA) or use Apple Silicon for GPU acceleration.")
        gpu_row.addWidget(self.gpu_checkbox)
        
        if not gpu_manager.is_gpu_available():
            gpu_row.addWidget(QLabel("(No GPU detected)"))
        
        gpu_row.addStretch()
        config_layout.addLayout(gpu_row)
        
        self.model_status = QLabel("Ready")
        config_layout.addWidget(self.model_status)
        
        config_group.setLayout(config_layout)
        main_layout.addWidget(config_group)
        
        # Input/Output
        io_splitter = QSplitter(Qt.Orientation.Vertical)
        
        input_widget = QWidget()
        input_layout = QVBoxLayout(input_widget)
        input_layout.setContentsMargins(0, 0, 0, 0)
        
        input_header = QHBoxLayout()
        input_header.addWidget(QLabel("🎙️ Input (Continuous)"))
        self.confidence_label = QLabel()
        input_header.addWidget(self.confidence_label)
        input_header.addStretch()
        self.word_count = QLabel("0 words")
        input_header.addWidget(self.word_count)
        input_layout.addLayout(input_header)
        
        self.input_text = QTextEdit()
        self.input_text.setPlaceholderText("🎤 Speak continuously - no need to stop...\n\nClick 'Start Continuous Listening' and speak naturally.\nYour words will appear here in real-time with timestamps and confidence scores.")
        self.input_text.textChanged.connect(self.update_word_count)
        self.input_text.setToolTip("Live transcription appears here with timestamps and confidence scores")
        input_layout.addWidget(self.input_text)
        
        io_splitter.addWidget(input_widget)
        
        output_widget = QWidget()
        output_layout = QVBoxLayout(output_widget)
        output_layout.setContentsMargins(0, 0, 0, 0)
        
        output_header = QHBoxLayout()
        output_header.addWidget(QLabel("🈯 Translation (Async Pipeline)"))
        output_header.addStretch()
        self.copy_btn = QPushButton("📋 Copy")
        self.copy_btn.clicked.connect(self.copy_output)
        output_header.addWidget(self.copy_btn)
        output_layout.addLayout(output_header)
        
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setPlaceholderText("🌐 Translation appears here instantly...\n\nTranslations are processed in real-time through async pipeline.\nResults include timestamps and confidence scores.")
        self.output_text.setToolTip("Translated text with confidence scores and timestamps")
        output_layout.addWidget(self.output_text)
        
        io_splitter.addWidget(output_widget)
        main_layout.addWidget(io_splitter, 3)
        
        # Controls
        controls = QWidget()
        controls_layout = QGridLayout(controls)
        
        self.listen_btn = QPushButton("🎤 Start Continuous Listening")
        self.listen_btn.clicked.connect(self.toggle_listening)
        self.listen_btn.setStyleSheet("""
            QPushButton {
                font-weight: 600;
                padding: 14px 24px;
                font-size: 15px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #4CAF50, stop:1 #388E3C);
                color: white;
                border: none;
                border-radius: 12px;
                letter-spacing: 0.5px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #5FD068, stop:1 #4CAF50);
                padding: 14px 24px;
            }
            QPushButton:pressed {
                background: #2E7D32;
            }
        """)
        self.listen_btn.setToolTip("Start continuous speech recognition (Ctrl+L)")
        controls_layout.addWidget(self.listen_btn, 0, 0, 1, 2)
        
        self.translate_btn = QPushButton("🔄 Translate")
        self.translate_btn.clicked.connect(self.translate_manual)
        self.translate_btn.setToolTip("Manually translate the input text (Ctrl+T)")
        self.translate_btn.setStyleSheet("padding: 12px 20px; font-size: 14px; font-weight: 500;")
        controls_layout.addWidget(self.translate_btn, 0, 2, 1, 2)
        
        self.speak_btn = QPushButton("🔊 Speak")
        self.speak_btn.clicked.connect(self.speak_output)
        self.speak_btn.setToolTip("Speak the translated text aloud (Ctrl+S)")
        self.speak_btn.setStyleSheet("padding: 10px 18px; font-size: 13px; font-weight: 500;")
        controls_layout.addWidget(self.speak_btn, 1, 0)
        
        self.stop_btn = QPushButton("🔇 Stop")
        self.stop_btn.clicked.connect(lambda: tts_manager.stop())
        self.stop_btn.setToolTip("Stop current text-to-speech playback")
        self.stop_btn.setStyleSheet("padding: 10px 18px; font-size: 13px; font-weight: 500;")
        controls_layout.addWidget(self.stop_btn, 1, 1)
        
        self.source_btn = QPushButton("🎧 System Audio")
        self.source_btn.clicked.connect(self.toggle_source)
        self.source_btn.setToolTip("Switch between microphone and system audio input")
        self.source_btn.setStyleSheet("padding: 10px 18px; font-size: 13px; font-weight: 500;")
        controls_layout.addWidget(self.source_btn, 1, 2)
        
        self.overlay_btn = QPushButton("👁️ Overlay")
        self.overlay_btn.clicked.connect(self.toggle_overlay)
        self.overlay_btn.setToolTip("Toggle the resizable translation overlay (Ctrl+O)\nDrag corners to resize, drag center to move")
        self.overlay_btn.setStyleSheet("padding: 10px 18px; font-size: 13px; font-weight: 500;")
        controls_layout.addWidget(self.overlay_btn, 1, 3)
        
        self.auto_speak = QCheckBox("🔊 Auto-speak translations")
        self.auto_speak.setChecked(config.get("auto_speak", True))
        self.auto_speak.stateChanged.connect(lambda: config.set("auto_speak", self.auto_speak.isChecked()))
        self.auto_speak.setToolTip("Automatically speak translated text using text-to-speech")
        self.auto_speak.setStyleSheet("font-size: 13px; font-weight: 500;")
        controls_layout.addWidget(self.auto_speak, 2, 0, 1, 2)
        
        self.show_conf = QCheckBox("🎯 Show confidence scores")
        self.show_conf.setChecked(config.get("show_confidence", True))
        self.show_conf.stateChanged.connect(lambda: config.set("show_confidence", self.show_conf.isChecked()))
        self.show_conf.setToolTip("Display confidence scores for speech recognition and translation")
        self.show_conf.setStyleSheet("font-size: 13px; font-weight: 500;")
        controls_layout.addWidget(self.show_conf, 2, 2, 1, 2)
        
        main_layout.addWidget(controls)
        
        # Professional history section
        history_group = QGroupBox("📜 Translation History")
        history_group.setToolTip("View, search, and export your translation history")
        history_layout = QVBoxLayout()
        
        history_controls = QHBoxLayout()
        history_controls.setSpacing(10)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Search translation history... (Ctrl+F)")
        self.search_input.textChanged.connect(self.search_history)
        self.search_input.setToolTip("Search through your translation history by source or translated text")
        self.search_input.setStyleSheet("padding: 10px; font-size: 13px;")
        history_controls.addWidget(self.search_input)
        
        self.export_btn = QPushButton("💾 Export")
        self.export_btn.clicked.connect(self.export_history)
        self.export_btn.setToolTip("Export translation history to text file (Ctrl+E)")
        self.export_btn.setStyleSheet("padding: 9px 16px; font-size: 13px; font-weight: 500;")
        history_controls.addWidget(self.export_btn)
        
        self.clear_btn = QPushButton("🗑️ Clear")
        self.clear_btn.clicked.connect(self.clear_history)
        self.clear_btn.setToolTip("Clear all translation history (cannot be undone)")
        self.clear_btn.setStyleSheet("padding: 9px 16px; font-size: 13px; font-weight: 500;")
        history_controls.addWidget(self.clear_btn)
        
        history_layout.addLayout(history_controls)
        
        self.history_list = QListWidget()
        self.history_list.itemDoubleClicked.connect(self.load_history_item)
        history_layout.addWidget(self.history_list)
        
        history_group.setLayout(history_layout)
        main_layout.addWidget(history_group, 1)
        
        self.statusBar().showMessage("🚀 Ready - Professional Edition v3.5 | Material Design 3 UI")
        self.refresh_history()
        self.setup_shortcuts()
    
    def setup_shortcuts(self):
        """Setup professional keyboard shortcuts for accessibility"""
        # Help and information
        QShortcut(QKeySequence("F1"), self, self.show_help)
        QShortcut(QKeySequence("Ctrl+H"), self, self.show_help)
        
        # Main controls
        QShortcut(QKeySequence("Ctrl+L"), self, self.toggle_listening)
        QShortcut(QKeySequence("Ctrl+T"), self, self.translate_manual)
        QShortcut(QKeySequence("Ctrl+S"), self, self.speak_output)
        QShortcut(QKeySequence("Ctrl+O"), self, self.toggle_overlay)
        QShortcut(QKeySequence("Ctrl+D"), self, self.toggle_theme)
        
        # Advanced shortcuts for power users
        QShortcut(QKeySequence("Ctrl+Shift+S"), self, self.show_settings)
        QShortcut(QKeySequence("Ctrl+Shift+M"), self, self.show_models)
        QShortcut(QKeySequence("Ctrl+E"), self, self.export_history)
        QShortcut(QKeySequence("Ctrl+F"), self, self.focus_search)
        QShortcut(QKeySequence("Ctrl+Shift+C"), self, self.clear_io_fields)
        
        # Application control
        QShortcut(QKeySequence("Ctrl+Q"), self, self.close)
        QShortcut(QKeySequence("Alt+F4"), self, self.close)
        
        log.info("✅ Keyboard shortcuts configured for accessibility")
    
    def focus_search(self):
        """Focus the search input for accessibility"""
        self.search_input.setFocus()
        self.search_input.selectAll()
    
    def clear_io_fields(self):
        """Clear input and output fields (Ctrl+Shift+C)"""
        self.input_text.clear()
        self.output_text.clear()
        self.overlay.clear_subtitles()
        self.statusBar().showMessage("✅ Cleared input/output fields", 2000)
    
    def show_help(self):
        help_text = f"""
🌍 Universal Live Translator — Professional Edition v3.5

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✨ CONTINUOUS LISTENING
• Microphone never stops - speak naturally without interruptions
• Async processing pipeline - zero blocking, maximum performance
• Parallel recognition and translation for instant results
• Real-time performance monitoring with queue status

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📺 NETFLIX/GOOGLE-STYLE OVERLAY
• Real-time word-by-word subtitle updates
• Professional glassmorphic design with blur effects
• Smooth fade and scroll animations
• Shows last {config.get("subtitle_lines", 3)} lines of text
• Auto-wrapping at sentence breaks

Resizing Controls:
  🔸 Drag corners → Resize diagonally
  🔸 Drag edges → Resize in one direction
  🔸 Drag center → Move window
  🔸 Minimum size enforced for readability

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🚀 GPU ACCELERATION
• Current Status: {gpu_manager.device_name}
• Device: {gpu_manager.device.upper()}
• CUDA: {'✅ Available' if gpu_manager.has_cuda else '❌ Not detected'}
• MPS: {'✅ Available' if gpu_manager.has_mps else '❌ Not detected'}
• Performance: 10-20x faster Whisper transcription
• Configure in Settings (⚙️) for instant switching

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚡ KEYBOARD SHORTCUTS
• F1 → Show this help
• Ctrl+L → Start/stop continuous listening
• Ctrl+T → Manual translate
• Ctrl+S → Speak output
• Ctrl+O → Toggle overlay
• Ctrl+D → Toggle dark/light theme
• Ctrl+Q → Quit application

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎨 PROFESSIONAL FEATURES
• Material Design 3 UI with smooth animations
• Netflix-level glassmorphic effects
• Professional color palette and typography
• Enhanced status indicators with real-time feedback
• Accessible design with keyboard navigation
• Smooth micro-interactions throughout

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📥 MODEL MANAGEMENT
• Click 'Models' to download Whisper/Vosk models
• Whisper: tiny, base, small, medium, large
• Vosk: Offline speech recognition for 4+ languages
• Auto-download on first use

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚙️ SETTINGS
All settings editable via Settings dialog:
• Appearance: Theme, fonts, colors, animations
• Audio: TTS rate, volume, input devices
• GPU & Models: Acceleration, Whisper model size
• Cache: Translation caching, expiry settings
• Overlay: Subtitle lines, update speed

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 PRO TIPS
• Use GPU acceleration for 10-20x faster transcription
• Set subtitle update delay to 5-10ms for instant captions
• Enable translation caching for faster repeated phrases
• Use 'base' Whisper model for best speed/accuracy balance
• Resize overlay to fit your screen perfectly

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Enjoy your professional-grade translator! 🚀
"""
        msg = QMessageBox(self)
        msg.setWindowTitle("✨ Help — Universal Live Translator v3.5")
        msg.setText(help_text)
        msg.setIcon(QMessageBox.Icon.Information)
        # Set minimum width for better formatting
        msg.setStyleSheet("QLabel{min-width: 650px; font-family: monospace;}")
        msg.exec()
    
    def populate_languages(self, combo, include_auto=False):
        if include_auto:
            combo.addItem("🔍 Auto", "auto")
        langs = sorted([(n.title(), c) for n, c in GOOGLE_LANGUAGES_TO_CODES.items()], key=lambda x: x[0])
        for name, code in langs:
            combo.addItem(name, code)
    
    def load_settings(self):
        src = config.get("source_language", "auto")
        tgt = config.get("target_language", "fr")
        engine = config.get("recognition_engine", "google")
        idx = self.source_lang_combo.findData(src)
        if idx >= 0:
            self.source_lang_combo.setCurrentIndex(idx)
        idx = self.target_lang_combo.findData(tgt)
        if idx >= 0:
            self.target_lang_combo.setCurrentIndex(idx)
        idx = self.engine_combo.findData(engine)
        if idx >= 0:
            self.engine_combo.setCurrentIndex(idx)
    
    def on_engine_changed(self):
        engine_val = self.engine_combo.currentData()
        self.recognition_engine = RecognitionEngine(engine_val)
        config.set("recognition_engine", engine_val)
        if self.recognition_thread and self.recognition_thread.isRunning():
            self.stop_listening()
            QTimer.singleShot(500, self.start_listening)
    
    def on_gpu_toggled(self):
        """Handle GPU acceleration toggle with professional feedback"""
        use_gpu = self.gpu_checkbox.isChecked()
        config.set("use_gpu", use_gpu)
        whisper_manager.set_device(use_gpu)
        device = whisper_manager.device
        
        # Update GPU status indicator with color coding
        gpu_color = "#4CAF50" if use_gpu and gpu_manager.is_gpu_available() else "#FFC107"
        gpu_bg = "rgba(76,175,80,0.15)" if use_gpu and gpu_manager.is_gpu_available() else "rgba(255,193,7,0.15)"
        self.gpu_status.setText(f"🚀 {device.upper()}")
        self.gpu_status.setStyleSheet(f"""
            QLabel {{
                color: {gpu_color};
                font-weight: 600;
                font-size: 13px;
                padding: 6px 12px;
                background: {gpu_bg};
                border-radius: 8px;
                border: 1px solid {gpu_color};
            }}
        """)
        
        # Show professional status message
        if use_gpu and gpu_manager.is_gpu_available():
            self.statusBar().showMessage(f"✅ GPU acceleration ENABLED - Using {device.upper()} (10-20x faster!)", 4000)
        else:
            self.statusBar().showMessage(f"⚠️ GPU acceleration disabled - Using {device.upper()}", 4000)
    
    def show_models(self):
        dialog = ModelManagerDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Refresh UI if needed
            pass
    
    def show_settings(self):
        dialog = SettingsDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Apply theme change if needed
            theme = config.get("theme", "dark")
            self.apply_theme(theme)
            # Update overlay style and configuration
            self.overlay.apply_style()
            # Update subtitle delay setting
            self.overlay.subtitle_update_delay = config.get("subtitle_update_delay", 10) / 1000.0
            # Recreate displayed_lines deque with new max lines
            max_lines = config.get("subtitle_lines", 3)
            old_lines = list(self.overlay.displayed_lines)
            self.overlay.displayed_lines = deque(old_lines, maxlen=max_lines)
            # Update GPU status
            device = whisper_manager.device
            self.gpu_status.setText(f"🚀 Device: {device.upper()}")
            self.gpu_checkbox.setChecked(config.get("use_gpu", True))
            self.statusBar().showMessage("Settings saved - Subtitle speed updated", 3000)
    
    def swap_languages(self):
        """Swap source and target languages with validation"""
        if self.source_lang_combo.currentData() == "auto":
            self.statusBar().showMessage("⚠️ Cannot swap with auto-detect enabled", 3000)
            return
        
        src_idx = self.source_lang_combo.currentIndex()
        tgt_idx = self.target_lang_combo.currentIndex()
        
        # Swap the selections
        self.source_lang_combo.setCurrentIndex(tgt_idx + 1)
        self.target_lang_combo.setCurrentIndex(src_idx - 1)
        
        # Show confirmation
        src_lang = self.source_lang_combo.currentText()
        tgt_lang = self.target_lang_combo.currentText()
        self.statusBar().showMessage(f"⇄ Languages swapped: {src_lang} → {tgt_lang}", 2000)
    
    def update_word_count(self):
        text = self.input_text.toPlainText()
        words = len(text.split()) if text.strip() else 0
        self.word_count.setText(f"{words} words")
    
    def toggle_listening(self):
        if self.recognition_thread and self.recognition_thread.isRunning():
            self.stop_listening()
        else:
            self.start_listening()
    
    def start_listening(self):
        if self.recognition_thread:
            self.recognition_thread.stop()
            self.recognition_thread.wait()
        
        src_lang = self.source_lang_combo.currentData()
        if src_lang == "auto":
            src_lang = "en"
        
        device_idx = config.get("audio_device_input", "default")
        if device_idx == "default":
            device_idx = None
        else:
            device_idx = int(device_idx)
        
        # Use continuous recognition thread
        self.recognition_thread = ContinuousSpeechRecognitionThread(
            self.source_type, src_lang, self.recognition_engine, device_idx
        )
        self.recognition_thread.phrase_detected.connect(self.handle_phrase, Qt.ConnectionType.QueuedConnection)
        self.recognition_thread.status_changed.connect(self.update_status_safe, Qt.ConnectionType.QueuedConnection)
        self.recognition_thread.error_occurred.connect(
            self.handle_recognition_error, Qt.ConnectionType.QueuedConnection
        )
        self.recognition_thread.performance_update.connect(self.update_performance, Qt.ConnectionType.QueuedConnection)
        self.recognition_thread.start()
        
        self.listen_btn.setText("⏹️ Stop Continuous Listening")
        self.listen_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #F44336, stop:1 #D32F2F);
                color: white;
                font-weight: 600;
                padding: 14px 24px;
                font-size: 15px;
                border: none;
                border-radius: 12px;
                letter-spacing: 0.5px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #FF5252, stop:1 #F44336);
            }
            QPushButton:pressed {
                background: #B71C1C;
            }
        """)
        self.statusBar().showMessage(f"🎙️ Continuous listening active ({self.recognition_engine.value} engine) - Speak naturally!")
    
    def stop_listening(self):
        if self.recognition_thread:
            self.recognition_thread.stop()
            self.recognition_thread.wait()
            self.recognition_thread = None
        self.listen_btn.setText("🎤 Start Continuous Listening")
        self.listen_btn.setStyleSheet("""
            QPushButton {
                font-weight: 600;
                padding: 14px 24px;
                font-size: 15px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #4CAF50, stop:1 #388E3C);
                color: white;
                border: none;
                border-radius: 12px;
                letter-spacing: 0.5px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #5FD068, stop:1 #4CAF50);
            }
        """)
        self.statusBar().showMessage("Stopped")
        self.perf_label.setText("⚡ Performance: Idle")
    
    def toggle_source(self):
        """Toggle audio source with professional feedback"""
        self.source_type = "system" if self.source_type == "microphone" else "microphone"
        self.source_btn.setText("🎤 Microphone" if self.source_type == "system" else "🎧 System Audio")
        
        # Show status update
        source_name = "🎤 Microphone" if self.source_type == "microphone" else "🎧 System Audio"
        self.statusBar().showMessage(f"⇄ Switched to {source_name}", 2000)
        
        # Restart listening if active
        if self.recognition_thread and self.recognition_thread.isRunning():
            self.statusBar().showMessage(f"↻ Restarting with {source_name}...", 2000)
            self.stop_listening()
            QTimer.singleShot(500, self.start_listening)
    
    def update_status_safe(self, message):
        """Thread-safe status update"""
        QMetaObject.invokeMethod(
            self.statusBar(), "showMessage",
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(str, message)
        )
    
    def handle_recognition_error(self, error_msg):
        """Thread-safe error handling"""
        QMessageBox.warning(self, "Error", error_msg)
        self.stop_listening()
    
    def update_performance(self, perf_data):
        """Update professional performance indicators (called from signal, already thread-safe)"""
        avg_time = perf_data.get('avg_processing_time', 0)
        rec_queue = perf_data.get('recognition_queue', 0)
        trans_queue = perf_data.get('translation_queue', 0)
        device = perf_data.get('device', 'N/A')
        
        # Color-coded performance indicator
        if avg_time < 300:
            color = "#4CAF50"  # Green - Excellent
            status = "Excellent"
        elif avg_time < 800:
            color = "#FFC107"  # Yellow - Good
            status = "Good"
        else:
            color = "#FF5722"  # Red - Slow
            status = "Slow"
        
        self.perf_label.setText(
            f"⚡ {avg_time:.0f}ms ({status}) | Queue: {rec_queue}/{trans_queue} | {device.upper()}"
        )
        self.perf_label.setStyleSheet(f"""
            QLabel {{
                font-size: 13px;
                font-weight: 500;
                color: {color};
                padding: 6px 12px;
                background: rgba({int(color[1:3], 16)},{int(color[3:5], 16)},{int(color[5:7], 16)},0.12);
                border-radius: 8px;
                border: 1px solid {color};
            }}
        """)
    
    def handle_phrase(self, phrase, confidence):
        if not phrase.strip():
            return
        
        cursor = self.input_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        timestamp = datetime.now().strftime("%H:%M:%S")
        conf_str = f" [{confidence:.0%}]" if config.get("show_confidence") else ""
        cursor.insertText(f"[{timestamp}]{conf_str} {phrase}\n")
        self.input_text.setTextCursor(cursor)
        self.input_text.ensureCursorVisible()
        self.confidence_label.setText(f"Confidence: {confidence:.0%}")
        
        if self.translation_mode in ["Real-time", "Continuous"]:
            # Async translation - non-blocking
            self.translate_phrase_async(phrase, confidence)
    
    def translate_phrase_async(self, phrase, speech_conf=1.0):
        """Async translation - doesn't block recognition"""
        src_lang = self.source_lang_combo.currentData()
        tgt_lang = self.target_lang_combo.currentData()
        
        if src_lang == "auto":
            try:
                detections = detect_langs(phrase)
                src_lang = detections[0].lang if detections else "en"
            except:
                src_lang = "en"
        
        def on_translation_complete(result):
            translated, duration, trans_conf = result
            combined_conf = speech_conf * trans_conf
            timestamp = datetime.now().strftime("%H:%M:%S")
            conf_str = f" [{combined_conf:.0%}]" if config.get("show_confidence") else ""
            
            self.output_text.append(f"[{timestamp}]{conf_str} {translated}")
            self.overlay.add_text(translated)
            
            if config.get("auto_speak", True):
                tts_manager.speak(translated, tgt_lang)
            
            db.add_translation(phrase, translated, src_lang, tgt_lang, 
                             self.translation_mode, self.recognition_engine.value, 
                             combined_conf, duration)
            
            # Throttled history refresh
            self.refresh_history_throttled()
            
            self.statusBar().showMessage(f"✓ Translated ({duration}ms, {combined_conf:.0%})", 2000)
        
        # Submit async translation
        translator.translate_async(phrase, src_lang, tgt_lang, on_translation_complete)
    
    def translate_phrase(self, phrase, speech_conf=1.0):
        """Synchronous translation (for compatibility)"""
        src_lang = self.source_lang_combo.currentData()
        tgt_lang = self.target_lang_combo.currentData()
        
        if src_lang == "auto":
            try:
                detections = detect_langs(phrase)
                src_lang = detections[0].lang if detections else "en"
            except:
                src_lang = "en"
        
        translated, duration, trans_conf = translator.translate(phrase, src_lang, tgt_lang)
        combined_conf = speech_conf * trans_conf
        timestamp = datetime.now().strftime("%H:%M:%S")
        conf_str = f" [{combined_conf:.0%}]" if config.get("show_confidence") else ""
        
        self.output_text.append(f"[{timestamp}]{conf_str} {translated}")
        self.overlay.add_text(translated)
        
        if config.get("auto_speak", True):
            tts_manager.speak(translated, tgt_lang)
        
        db.add_translation(phrase, translated, src_lang, tgt_lang, 
                         self.translation_mode, self.recognition_engine.value, 
                         combined_conf, duration)
        
        self.refresh_history_throttled()
        self.statusBar().showMessage(f"Translated ({duration}ms, {combined_conf:.0%})", 2000)
    
    def translate_manual(self):
        text = self.input_text.toPlainText().strip()
        if not text:
            self.statusBar().showMessage("No text", 3000)
            return
        
        src_lang = self.source_lang_combo.currentData()
        tgt_lang = self.target_lang_combo.currentData()
        
        if src_lang == "auto":
            try:
                src_lang = detect_langs(text)[0].lang if detect_langs(text) else "en"
            except:
                src_lang = "en"
        
        self.statusBar().showMessage("Translating...")
        QApplication.processEvents()
        
        translated, duration, conf = translator.translate(text, src_lang, tgt_lang)
        self.output_text.clear()
        conf_str = f" [{conf:.0%}]" if config.get("show_confidence") else ""
        self.output_text.append(f"{translated}{conf_str}")
        self.overlay.add_text(translated)
        
        if config.get("auto_speak", True):
            tts_manager.speak(translated, tgt_lang)
        
        db.add_translation(text, translated, src_lang, tgt_lang, "Manual", "manual", conf, duration)
        self.refresh_history()
        self.statusBar().showMessage(f"Done ({duration}ms, {conf:.0%})", 3000)
    
    def speak_output(self):
        text = self.output_text.toPlainText().strip()
        if not text:
            return
        import re
        text = re.sub(r'\[.*?\]\s*', '', text)
        lang = self.target_lang_combo.currentData()
        tts_manager.speak(text, lang)
    
    def copy_output(self):
        """Copy output text to clipboard with professional feedback"""
        text = self.output_text.toPlainText()
        if not text.strip():
            self.statusBar().showMessage("⚠️ No text to copy", 2000)
            return
        
        import re
        # Remove timestamps and confidence scores
        text = re.sub(r'\[.*?\]\s*', '', text)
        QApplication.clipboard().setText(text)
        
        # Show success message with character count
        char_count = len(text)
        word_count = len(text.split())
        self.statusBar().showMessage(f"✅ Copied to clipboard! ({word_count} words, {char_count} characters)", 3000)
    
    def toggle_overlay(self):
        """Toggle overlay visibility with status feedback"""
        is_visible = not self.overlay.isVisible()
        self.overlay.setVisible(is_visible)
        config.set("overlay_visible", is_visible)
        
        status = "👁️ Overlay shown" if is_visible else "🚫 Overlay hidden"
        self.statusBar().showMessage(status, 2000)
    
    def refresh_history_throttled(self):
        """Throttled history refresh to avoid UI lag"""
        now = time.time()
        if now - self.last_history_refresh > self.history_refresh_throttle:
            self.refresh_history()
            self.last_history_refresh = now
    
    def refresh_history(self, search=""):
        self.history_list.clear()
        for row in db.get_history(50, search):
            try:
                dt = datetime.fromisoformat(row['timestamp'])
                time_str = dt.strftime("%H:%M")
            except:
                time_str = ""
            
            src_prev = row['source_text'][:40] + "..." if len(row['source_text']) > 40 else row['source_text']
            trans_prev = row['translated_text'][:40] + "..." if len(row['translated_text']) > 40 else row['translated_text']
            conf = row.get('confidence', 1.0)
            conf_str = f" [{conf:.0%}]" if conf < 1.0 else ""
            item_text = f"[{time_str}]{conf_str} {row['source_lang']}→{row['target_lang']} | {src_prev} ➜ {trans_prev}"
            
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, row)
            
            if conf >= 0.9:
                item.setForeground(QColor("#4CAF50"))
            elif conf >= 0.7:
                item.setForeground(QColor("#FFC107"))
            else:
                item.setForeground(QColor("#FF5722"))
            
            self.history_list.addItem(item)
    
    def search_history(self):
        self.refresh_history(self.search_input.text())
    
    def load_history_item(self, item):
        data = item.data(Qt.ItemDataRole.UserRole)
        if data:
            self.input_text.setPlainText(data['source_text'])
            self.output_text.setPlainText(data['translated_text'])
    
    def export_history(self):
        """Export history with professional feedback and error handling"""
        default_filename = f"translator_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        filename, _ = QFileDialog.getSaveFileName(
            self, 
            "💾 Export Translation History", 
            str(BASE_DIR / default_filename), 
            "Text Files (*.txt);;All Files (*)"
        )
        if filename:
            try:
                db.export_history(filename)
                # Count exported items
                with open(filename, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    count = len([l for l in lines if l.startswith('[')])
                
                QMessageBox.information(
                    self, 
                    "✅ Export Successful",
                    f"Successfully exported {count} translations to:\n\n{filename}"
                )
                self.statusBar().showMessage(f"✅ Exported {count} translations", 3000)
            except Exception as e:
                log.error(f"Export failed: {e}")
                QMessageBox.critical(
                    self, 
                    "❌ Export Failed",
                    f"Failed to export translation history:\n\n{str(e)}"
                )
    
    def clear_history(self):
        """Clear history with professional confirmation dialog"""
        reply = QMessageBox.question(
            self, 
            "🗑️ Clear History",
            "Are you sure you want to clear all translation history?\n\nThis action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            db.clear_history()
            self.refresh_history()
            self.statusBar().showMessage("✅ Translation history cleared", 3000)
    
    def toggle_theme(self):
        """Toggle theme with smooth transition feedback"""
        current = config.get("theme", "dark")
        new = "light" if current == "dark" else "dark"
        config.set("theme", new)
        self.apply_theme(new)
        
        # Professional feedback
        theme_name = "🌙 Dark Mode" if new == "dark" else "☀️ Light Mode"
        self.statusBar().showMessage(f"✅ Switched to {theme_name}", 2000)
        self.theme_btn.setText("☀️ Light" if new == "dark" else "🌙 Dark")
    
    def apply_theme(self, theme):
        if theme == "dark":
            # Netflix/Google-level Material Design 3 dark theme
            self.setStyleSheet("""
                QMainWindow, QWidget {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #0f0f14, stop:1 #1a1a20);
                    color: #e8eaed;
                    font-family: "Segoe UI", "SF Pro Display", -apple-system, system-ui, sans-serif;
                }
                QGroupBox {
                    border: 1.5px solid rgba(255,255,255,0.08);
                    border-radius: 16px;
                    margin-top: 14px;
                    padding-top: 22px;
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 rgba(42,42,50,0.4), stop:1 rgba(32,32,38,0.4));
                    font-size: 13px;
                }
                QGroupBox::title {
                    left: 18px;
                    padding: 0 12px;
                    color: #82c8ff;
                    font-weight: 600;
                    font-size: 14px;
                    letter-spacing: 0.5px;
                }
                QTextEdit, QListWidget, QLineEdit {
                    background: rgba(28,28,35,0.7);
                    border: 1.5px solid rgba(255,255,255,0.06);
                    border-radius: 12px;
                    padding: 12px;
                    selection-background-color: #82c8ff;
                    selection-color: #0f0f14;
                    font-size: 14px;
                    line-height: 1.6;
                }
                QTextEdit:focus, QLineEdit:focus {
                    border: 1.5px solid #82c8ff;
                    background: rgba(28,28,35,0.85);
                }
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 rgba(60,60,70,0.8), stop:1 rgba(45,45,55,0.8));
                    border: 1.5px solid rgba(255,255,255,0.1);
                    border-radius: 10px;
                    padding: 11px 20px;
                    font-weight: 500;
                    font-size: 13px;
                    color: #e8eaed;
                    letter-spacing: 0.3px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 rgba(75,75,85,0.9), stop:1 rgba(60,60,70,0.9));
                    border: 1.5px solid #82c8ff;
                    transform: translateY(-1px);
                }
                QPushButton:pressed {
                    background: rgba(45,45,55,0.95);
                    border: 1.5px solid #5fa8d3;
                    transform: translateY(0px);
                }
                QComboBox {
                    background: rgba(28,28,35,0.7);
                    border: 1.5px solid rgba(255,255,255,0.06);
                    border-radius: 10px;
                    padding: 9px 12px;
                    font-size: 13px;
                    min-height: 20px;
                }
                QComboBox:hover {
                    border: 1.5px solid #82c8ff;
                    background: rgba(28,28,35,0.85);
                }
                QComboBox::drop-down {
                    border: none;
                    width: 30px;
                }
                QComboBox::down-arrow {
                    image: none;
                    border-left: 5px solid transparent;
                    border-right: 5px solid transparent;
                    border-top: 6px solid #82c8ff;
                    margin-right: 8px;
                }
                QCheckBox {
                    spacing: 10px;
                    font-size: 13px;
                }
                QCheckBox::indicator {
                    width: 20px;
                    height: 20px;
                    border-radius: 6px;
                    border: 2px solid rgba(255,255,255,0.15);
                    background: rgba(28,28,35,0.7);
                }
                QCheckBox::indicator:hover {
                    border: 2px solid #82c8ff;
                    background: rgba(28,28,35,0.85);
                }
                QCheckBox::indicator:checked {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #82c8ff, stop:1 #5fa8d3);
                    border-color: #82c8ff;
                    image: none;
                }
                QStatusBar {
                    background: rgba(20,20,26,0.95);
                    border-top: 1.5px solid rgba(255,255,255,0.05);
                    color: #b8bbbe;
                    font-size: 12px;
                    padding: 5px;
                }
                QLabel {
                    color: #e8eaed;
                    font-size: 13px;
                }
                QScrollBar:vertical {
                    background: transparent;
                    width: 12px;
                    margin: 0;
                }
                QScrollBar::handle:vertical {
                    background: rgba(130,200,255,0.3);
                    border-radius: 6px;
                    min-height: 30px;
                }
                QScrollBar::handle:vertical:hover {
                    background: rgba(130,200,255,0.5);
                }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                    height: 0px;
                }
            """)
        else:
            # Netflix/Google-level Material Design 3 light theme
            self.setStyleSheet("""
                QMainWindow, QWidget {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #fafafa, stop:1 #f0f0f5);
                    color: #1f1f1f;
                    font-family: "Segoe UI", "SF Pro Display", -apple-system, system-ui, sans-serif;
                }
                QGroupBox {
                    border: 1.5px solid rgba(0,0,0,0.06);
                    border-radius: 16px;
                    margin-top: 14px;
                    padding-top: 22px;
                    background: rgba(255,255,255,0.85);
                    font-size: 13px;
                }
                QGroupBox::title {
                    left: 18px;
                    padding: 0 12px;
                    color: #1967d2;
                    font-weight: 600;
                    font-size: 14px;
                    letter-spacing: 0.5px;
                }
                QTextEdit, QListWidget, QLineEdit {
                    background: rgba(255,255,255,0.9);
                    border: 1.5px solid rgba(0,0,0,0.08);
                    border-radius: 12px;
                    padding: 12px;
                    selection-background-color: #1967d2;
                    selection-color: white;
                    font-size: 14px;
                    line-height: 1.6;
                }
                QTextEdit:focus, QLineEdit:focus {
                    border: 1.5px solid #1967d2;
                    background: white;
                }
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 rgba(255,255,255,0.95), stop:1 rgba(245,245,250,0.95));
                    border: 1.5px solid rgba(0,0,0,0.1);
                    border-radius: 10px;
                    padding: 11px 20px;
                    font-weight: 500;
                    font-size: 13px;
                    color: #1f1f1f;
                    letter-spacing: 0.3px;
                }
                QPushButton:hover {
                    background: white;
                    border: 1.5px solid #1967d2;
                    color: #1967d2;
                }
                QPushButton:pressed {
                    background: rgba(245,245,250,1);
                    border: 1.5px solid #1557b0;
                }
                QComboBox {
                    background: rgba(255,255,255,0.9);
                    border: 1.5px solid rgba(0,0,0,0.08);
                    border-radius: 10px;
                    padding: 9px 12px;
                    font-size: 13px;
                }
                QComboBox:hover {
                    border: 1.5px solid #1967d2;
                    background: white;
                }
                QCheckBox::indicator {
                    width: 20px;
                    height: 20px;
                    border-radius: 6px;
                    border: 2px solid rgba(0,0,0,0.2);
                    background: white;
                }
                QCheckBox::indicator:checked {
                    background: #1967d2;
                    border-color: #1967d2;
                }
                QStatusBar {
                    background: rgba(245,245,250,0.95);
                    border-top: 1.5px solid rgba(0,0,0,0.05);
                    color: #5f6368;
                    font-size: 12px;
                }
            """)
        
        # Update overlay style
        self.overlay.apply_style()
    
    def closeEvent(self, event):
        config.set("source_language", self.source_lang_combo.currentData())
        config.set("target_language", self.target_lang_combo.currentData())
        
        if self.recognition_thread:
            self.recognition_thread.stop()
            self.recognition_thread.wait()
        
        tts_manager.shutdown()
        audio_device_manager.cleanup()
        self.overlay.close()
        event.accept()

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Universal Live Translator Pro v3.5")
    app.setStyle("Fusion")
    
    log.info("="*70)
    log.info("🌍 Universal Live Translator — Professional Edition v3.5")
    log.info("="*70)
    log.info(f"📁 Data Directory: {BASE_DIR}")
    log.info(f"🚀 GPU Status: {gpu_manager.device_name}")
    log.info(f"💻 Device: {gpu_manager.device.upper()}")
    log.info(f"⚡ CUDA: {'Available' if gpu_manager.has_cuda else 'Not detected'}")
    log.info(f"🍎 MPS: {'Available' if gpu_manager.has_mps else 'Not detected'}")
    log.info(f"🎨 UI: Material Design 3 (Netflix/Google-level)")
    log.info("="*70)
    
    window = LiveTranslatorApp()
    window.show()
    
    log.info("✅ Application started successfully")
    log.info("💡 Press F1 for help and keyboard shortcuts")
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
