"""Core functionality modules"""
from .translation_engine import TranslationEngine, translator
from .tts_manager import TTSManager, tts_manager
from .speech_recognition import ContinuousSpeechRecognitionThread
from .contextual_engine import ContextualTranslationEngine, contextual_engine
from .conversation_mode import ConversationMode, conversation_mode
from .offline_translation import EnhancedOfflineTranslation, offline_translator

__all__ = [
    'TranslationEngine', 'translator',
    'TTSManager', 'tts_manager',
    'ContinuousSpeechRecognitionThread',
    'ContextualTranslationEngine', 'contextual_engine',
    'ConversationMode', 'conversation_mode',
    'EnhancedOfflineTranslation', 'offline_translator'
]
