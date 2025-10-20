"""Whisper speech recognition model management"""
import logging
import numpy as np
import whisper
from config import config
from utils import gpu_manager

log = logging.getLogger("Translator")

class WhisperModelManager:
    """Manages Whisper model loading and transcription"""
    def __init__(self):
        self.models = {}
        self.device = "cpu"
        self.use_gpu = config.get("use_gpu", True)
        # Initialize device on startup - force GPU if available
        self.set_device(self.use_gpu)
        log.info(f"WhisperModelManager initialized with device: {self.device} (use_gpu={self.use_gpu})")
    
    def set_device(self, use_gpu=True):
        """Set the compute device for Whisper models"""
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
        """Load a Whisper model of specified size"""
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
        """Transcribe audio using Whisper"""
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

# Global instance
whisper_manager = WhisperModelManager()
