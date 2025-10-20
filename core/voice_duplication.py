"""Voice Duplication Engine using RVC models"""
import logging
import numpy as np
from typing import Optional, Tuple
from .rvc_manager import rvc_manager

log = logging.getLogger("Translator")

class VoiceDuplicationEngine:
    """
    Engine for voice duplication mode - translates speech while maintaining voice qualities
    Uses RVC (Retrieval-based Voice Conversion) models for voice cloning
    """
    
    def __init__(self):
        self.enabled = False
        self.current_model = None
        self.inference_params = {
            'pitch_shift': 0,
            'index_rate': 0.75,
            'filter_radius': 3,
            'volume_envelope': 1.0,
            'protect_voiceless': 0.5
        }
    
    def enable(self, model_name: Optional[str] = None) -> bool:
        """
        Enable voice duplication mode
        
        Args:
            model_name: Name of RVC model to use, or None to use current
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if model_name:
                if not rvc_manager.set_current_model(model_name):
                    log.error(f"Model not found: {model_name}")
                    return False
            
            model_info = rvc_manager.get_current_model_info()
            if not model_info:
                log.error("No RVC model selected for voice duplication")
                return False
            
            # Validate model
            is_valid, message = rvc_manager.validate_model(rvc_manager.get_current_model())
            if not is_valid:
                log.error(f"Invalid model: {message}")
                return False
            
            log.info(f"Voice duplication enabled with model: {rvc_manager.get_current_model()}")
            log.info(f"Model validation: {message}")
            
            self.enabled = True
            self.current_model = rvc_manager.get_current_model()
            return True
            
        except Exception as e:
            log.error(f"Failed to enable voice duplication: {e}")
            return False
    
    def disable(self):
        """Disable voice duplication mode"""
        self.enabled = False
        log.info("Voice duplication mode disabled")
    
    def is_enabled(self) -> bool:
        """Check if voice duplication is currently enabled"""
        return self.enabled
    
    def process_audio(self, audio_data: np.ndarray, sample_rate: int = 16000) -> Tuple[np.ndarray, bool]:
        """
        Process audio through voice duplication (voice conversion)
        
        Args:
            audio_data: Input audio as numpy array
            sample_rate: Sample rate of the audio
        
        Returns:
            (converted_audio, success)
        """
        if not self.enabled or not self.current_model:
            return audio_data, False
        
        try:
            # Get current model info
            model_info = rvc_manager.get_current_model_info()
            if not model_info:
                return audio_data, False
            
            # TODO: Implement actual RVC inference here
            # This would require integrating with RVC inference library
            # For now, we return the original audio as a placeholder
            
            log.debug(f"Voice duplication processing with model: {self.current_model}")
            log.debug(f"Audio shape: {audio_data.shape}, Sample rate: {sample_rate}")
            
            # Placeholder - actual implementation would call RVC model here
            converted_audio = audio_data  # Replace with actual RVC inference
            
            return converted_audio, True
            
        except Exception as e:
            log.error(f"Voice duplication processing failed: {e}")
            return audio_data, False
    
    def set_inference_params(self, **kwargs):
        """
        Set voice duplication inference parameters
        
        Available parameters:
            - pitch_shift: Pitch adjustment in semitones (-12 to 12)
            - index_rate: Index search ratio (0.0 to 1.0)
            - filter_radius: Median filtering radius for harvest algorithm
            - volume_envelope: Volume envelope mixing (0.0 to 1.0)
            - protect_voiceless: Protect voiceless consonants (0.0 to 0.5)
        """
        for key, value in kwargs.items():
            if key in self.inference_params:
                self.inference_params[key] = value
                log.info(f"Updated voice duplication param: {key} = {value}")
    
    def get_inference_params(self) -> dict:
        """Get current inference parameters"""
        return self.inference_params.copy()
    
    def get_status(self) -> dict:
        """Get current status of voice duplication engine"""
        return {
            'enabled': self.enabled,
            'current_model': self.current_model,
            'model_info': rvc_manager.get_current_model_info() if self.current_model else None,
            'inference_params': self.inference_params,
            'available_models': rvc_manager.list_models()
        }


# Global instance
voice_duplication = VoiceDuplicationEngine()
