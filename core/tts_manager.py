"""Text-to-Speech management with RVC voice duplication support"""
import os
import queue
import threading
import tempfile
import logging
import numpy as np
import pyttsx3
from gtts import gTTS
from pydub import AudioSegment
import simpleaudio as sa
from config import config
from config.constants import AUDIO_DIR
from utils.helpers import is_online

log = logging.getLogger("Translator")

# Import voice duplication if available
try:
    from .voice_duplication import voice_duplication
    HAS_VOICE_DUPLICATION = True
except ImportError:
    HAS_VOICE_DUPLICATION = False
    log.warning("Voice duplication not available")

class TTSManager:
    """Manages text-to-speech with queueing, volume control, and voice duplication"""
    def __init__(self):
        self.queue = queue.Queue()
        self.running = True
        self.current = None
        self.volume = config.get("volume", 0.8)
        self.temp_files = []
        self.use_voice_duplication = False
        self.custom_tts_mode = False  # Use custom RVC models
        threading.Thread(target=self._worker, daemon=True).start()
    
    def _worker(self):
        """Background worker thread for TTS processing"""
        while self.running:
            try:
                text, lang = self.queue.get(timeout=0.5)
                self._speak(text, lang)
            except queue.Empty:
                continue
            except Exception as e:
                log.warning(f"TTS error: {e}")
    
    def _speak(self, text, lang):
        """Speak text using online or offline TTS"""
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
        """Add text to TTS queue"""
        if text.strip():
            self.queue.put((text, lang))
    
    def stop(self):
        """Stop currently playing audio"""
        if self.current and self.current.is_playing():
            self.current.stop()
    
    def set_volume(self, volume):
        """Set volume (0.0 to 1.0)"""
        self.volume = max(0.0, min(1.0, volume))
    
    def enable_voice_duplication(self, enable: bool = True):
        """Enable or disable voice duplication mode"""
        if enable and not HAS_VOICE_DUPLICATION:
            log.warning("Voice duplication requested but not available")
            return False
        self.use_voice_duplication = enable
        log.info(f"Voice duplication {'enabled' if enable else 'disabled'}")
        return True
    
    def enable_custom_tts(self, enable: bool = True):
        """Enable or disable custom RVC TTS models"""
        self.custom_tts_mode = enable
        log.info(f"Custom TTS mode {'enabled' if enable else 'disabled'}")
    
    def is_voice_duplication_enabled(self) -> bool:
        """Check if voice duplication is enabled"""
        return self.use_voice_duplication and HAS_VOICE_DUPLICATION
    
    def shutdown(self):
        """Shutdown TTS manager"""
        self.running = False
        self.stop()

# Global instance
tts_manager = TTSManager()
