"""Core functionality modules"""
from .translation_engine import TranslationEngine, translator
from .tts_manager import TTSManager, tts_manager
from .speech_recognition import ContinuousSpeechRecognitionThread
from .contextual_engine import ContextualTranslationEngine, contextual_engine
from .conversation_mode import ConversationMode, conversation_mode
from .offline_translation import EnhancedOfflineTranslation, offline_translator
from .rvc_manager import RVCModelManager, rvc_manager
from .voice_duplication import VoiceDuplicationEngine, voice_duplication
from .translation_modes import TranslationMode, TranslationModeManager, translation_mode_manager
from .platform_integrations import Platform, PlatformIntegration, platform_integration

__all__ = [
    'TranslationEngine', 'translator',
    'TTSManager', 'tts_manager',
    'ContinuousSpeechRecognitionThread',
    'ContextualTranslationEngine', 'contextual_engine',
    'ConversationMode', 'conversation_mode',
    'EnhancedOfflineTranslation', 'offline_translator',
    'RVCModelManager', 'rvc_manager',
    'VoiceDuplicationEngine', 'voice_duplication',
    'TranslationMode', 'TranslationModeManager', 'translation_mode_manager',
    'Platform', 'PlatformIntegration', 'platform_integration'
]
