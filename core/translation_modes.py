"""Translation Modes Manager - Standard, Simultaneous, Universal"""
import logging
import time
from enum import Enum
from typing import Optional, Callable

log = logging.getLogger("Translator")

class TranslationMode(Enum):
    """Available translation modes"""
    STANDARD = "standard"  # Translates after sentence completion
    SIMULTANEOUS = "simultaneous"  # Near real-time translation and dubbing
    UNIVERSAL = "universal"  # Captures audio and translates in real-time to any language
    VOICE_DUPLICATION = "voice_duplication"  # Translates with voice quality preservation

class TranslationModeManager:
    """Manages different translation modes and their behaviors"""
    
    def __init__(self):
        self.current_mode = TranslationMode.STANDARD
        self.mode_config = {
            TranslationMode.STANDARD: {
                'name': 'Standard Mode',
                'description': 'Translates sentences after they are completed',
                'min_pause_duration': 1.5,  # seconds
                'buffer_sentences': True,
                'real_time': False,
                'voice_duplication': False
            },
            TranslationMode.SIMULTANEOUS: {
                'name': 'Simultaneous Mode',
                'description': 'Translates and dubs in near real-time',
                'min_pause_duration': 0.3,  # seconds
                'buffer_sentences': False,
                'real_time': True,
                'voice_duplication': False
            },
            TranslationMode.UNIVERSAL: {
                'name': 'Universal Mode',
                'description': 'Captures and translates audio in real-time to any language',
                'min_pause_duration': 0.5,  # seconds
                'buffer_sentences': False,
                'real_time': True,
                'voice_duplication': False,
                'auto_detect_language': True
            },
            TranslationMode.VOICE_DUPLICATION: {
                'name': 'Voice Duplication Mode',
                'description': 'Translates while maintaining your voice qualities',
                'min_pause_duration': 1.0,  # seconds
                'buffer_sentences': True,
                'real_time': False,
                'voice_duplication': True
            }
        }
        
        # Performance metrics
        self.metrics = {
            'translations_count': 0,
            'avg_latency_ms': 0,
            'last_translation_time': 0
        }
    
    def set_mode(self, mode: TranslationMode) -> bool:
        """
        Set the current translation mode
        
        Args:
            mode: TranslationMode enum value
        
        Returns:
            True if mode was set successfully
        """
        if mode not in TranslationMode:
            log.error(f"Invalid translation mode: {mode}")
            return False
        
        self.current_mode = mode
        config = self.mode_config[mode]
        log.info(f"Translation mode set to: {config['name']}")
        log.info(f"  Description: {config['description']}")
        log.info(f"  Real-time: {config['real_time']}")
        log.info(f"  Voice duplication: {config['voice_duplication']}")
        
        return True
    
    def get_current_mode(self) -> TranslationMode:
        """Get the current translation mode"""
        return self.current_mode
    
    def get_mode_config(self, mode: Optional[TranslationMode] = None) -> dict:
        """
        Get configuration for a specific mode or current mode
        
        Args:
            mode: TranslationMode or None for current mode
        
        Returns:
            Configuration dictionary
        """
        target_mode = mode if mode is not None else self.current_mode
        return self.mode_config[target_mode].copy()
    
    def is_real_time(self) -> bool:
        """Check if current mode is real-time"""
        return self.mode_config[self.current_mode]['real_time']
    
    def requires_voice_duplication(self) -> bool:
        """Check if current mode requires voice duplication"""
        return self.mode_config[self.current_mode].get('voice_duplication', False)
    
    def get_pause_duration(self) -> float:
        """Get minimum pause duration for current mode"""
        return self.mode_config[self.current_mode]['min_pause_duration']
    
    def should_buffer_sentences(self) -> bool:
        """Check if sentences should be buffered in current mode"""
        return self.mode_config[self.current_mode]['buffer_sentences']
    
    def auto_detect_language(self) -> bool:
        """Check if current mode uses automatic language detection"""
        return self.mode_config[self.current_mode].get('auto_detect_language', False)
    
    def record_translation(self, latency_ms: float):
        """Record metrics for a translation"""
        self.metrics['translations_count'] += 1
        
        # Update running average latency
        count = self.metrics['translations_count']
        current_avg = self.metrics['avg_latency_ms']
        self.metrics['avg_latency_ms'] = ((current_avg * (count - 1)) + latency_ms) / count
        self.metrics['last_translation_time'] = time.time()
    
    def get_metrics(self) -> dict:
        """Get performance metrics"""
        return {
            'mode': self.current_mode.value,
            'mode_name': self.mode_config[self.current_mode]['name'],
            **self.metrics,
            'time_since_last': time.time() - self.metrics['last_translation_time'] if self.metrics['last_translation_time'] > 0 else 0
        }
    
    def reset_metrics(self):
        """Reset performance metrics"""
        self.metrics = {
            'translations_count': 0,
            'avg_latency_ms': 0,
            'last_translation_time': 0
        }
        log.info("Translation metrics reset")
    
    def get_all_modes_info(self) -> dict:
        """Get information about all available modes"""
        return {
            mode.value: {
                'enum': mode,
                **config
            }
            for mode, config in self.mode_config.items()
        }
    
    def get_mode_description(self, mode: Optional[TranslationMode] = None) -> str:
        """Get human-readable description of a mode"""
        target_mode = mode if mode is not None else self.current_mode
        config = self.mode_config[target_mode]
        return f"{config['name']}: {config['description']}"


# Global instance
translation_mode_manager = TranslationModeManager()
