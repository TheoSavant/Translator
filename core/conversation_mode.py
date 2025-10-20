"""Conversation Mode with Bidirectional Auto-Detection"""
import logging
from typing import Optional, Tuple, List
from collections import deque
from langdetect import detect, detect_langs, LangDetectException
import time

log = logging.getLogger("Translator")

class ConversationMode:
    """
    Intelligent conversation mode that auto-detects language and translates bidirectionally.
    If Language A is detected -> translate to Language B
    If Language B is detected -> translate to Language A
    """
    
    def __init__(self):
        self.enabled = False
        self.language_a = "en"  # Primary language
        self.language_b = "fr"  # Secondary language
        self.last_detected_lang = None
        self.detection_history = deque(maxlen=20)  # Track detection patterns
        self.conversation_participants = {}  # Track who speaks which language
        
        # Language detection confidence thresholds
        self.min_confidence = 0.8
        self.min_text_length = 3  # Minimum characters for reliable detection
        
        # Auto mode settings
        self.auto_mode = False  # When true, works with any detected language pair
        self.detected_languages = set()  # Track all detected languages in session
        
    def enable(self, lang_a: str = "en", lang_b: str = "fr", auto_mode: bool = False):
        """
        Enable conversation mode with specified language pair
        
        Args:
            lang_a: Primary language code (e.g., 'en')
            lang_b: Secondary language code (e.g., 'fr')
            auto_mode: If True, automatically adapt to any detected language pair
        """
        self.enabled = True
        self.language_a = lang_a
        self.language_b = lang_b
        self.auto_mode = auto_mode
        log.info(f"Conversation mode enabled: {lang_a} ↔ {lang_b} (Auto: {auto_mode})")
    
    def disable(self):
        """Disable conversation mode"""
        self.enabled = False
        self.clear_history()
        log.info("Conversation mode disabled")
    
    def clear_history(self):
        """Clear conversation history"""
        self.detection_history.clear()
        self.detected_languages.clear()
        self.conversation_participants.clear()
        self.last_detected_lang = None
    
    def detect_language_with_confidence(self, text: str) -> Tuple[Optional[str], float]:
        """
        Detect language with confidence score
        
        Returns:
            (language_code, confidence) or (None, 0.0) if detection fails
        """
        if not text or len(text.strip()) < self.min_text_length:
            return None, 0.0
        
        try:
            # Get multiple language predictions
            detections = detect_langs(text)
            
            if detections and len(detections) > 0:
                # Get the most likely language
                top_detection = detections[0]
                lang_code = top_detection.lang
                confidence = top_detection.prob
                
                # Normalize language codes (langdetect uses different codes sometimes)
                lang_code = self._normalize_language_code(lang_code)
                
                log.debug(f"Detected: {lang_code} (confidence: {confidence:.2f}) - Text: {text[:50]}")
                return lang_code, confidence
            
        except LangDetectException as e:
            log.warning(f"Language detection failed: {e}")
        except Exception as e:
            log.error(f"Unexpected error in language detection: {e}")
        
        return None, 0.0
    
    def _normalize_language_code(self, lang_code: str) -> str:
        """Normalize language codes to standard 2-letter ISO codes"""
        # langdetect sometimes returns different codes
        normalization_map = {
            'zh-cn': 'zh',
            'zh-tw': 'zh',
            'pt-br': 'pt',
            'pt-pt': 'pt',
        }
        return normalization_map.get(lang_code.lower(), lang_code.lower()[:2])
    
    def get_target_language(self, text: str, source_lang: Optional[str] = None) -> Tuple[str, str, float]:
        """
        Determine source and target languages based on conversation mode
        
        Args:
            text: Input text
            source_lang: Optional pre-detected source language
        
        Returns:
            (source_language, target_language, confidence)
        """
        if not self.enabled:
            # If conversation mode is disabled, return default
            return source_lang or "auto", self.language_b, 1.0
        
        # Detect language if not provided
        if not source_lang or source_lang == "auto":
            detected_lang, confidence = self.detect_language_with_confidence(text)
            if not detected_lang or confidence < self.min_confidence:
                # Fallback to last detected or default
                detected_lang = self.last_detected_lang or self.language_a
                confidence = 0.5
        else:
            detected_lang = source_lang
            confidence = 1.0
        
        # Record detection
        self.detection_history.append({
            'lang': detected_lang,
            'confidence': confidence,
            'timestamp': time.time()
        })
        self.detected_languages.add(detected_lang)
        self.last_detected_lang = detected_lang
        
        # Determine target based on detected language
        target_lang = self._determine_target_language(detected_lang)
        
        log.debug(f"Conversation routing: {detected_lang} → {target_lang} (confidence: {confidence:.2f})")
        
        return detected_lang, target_lang, confidence
    
    def _determine_target_language(self, source_lang: str) -> str:
        """
        Determine target language based on source and conversation mode settings
        """
        # Normalize for comparison
        source_normalized = source_lang.lower()[:2]
        lang_a_normalized = self.language_a.lower()[:2]
        lang_b_normalized = self.language_b.lower()[:2]
        
        if self.auto_mode:
            # In auto mode, intelligently pair languages
            if source_normalized == lang_a_normalized:
                return self.language_b
            elif source_normalized == lang_b_normalized:
                return self.language_a
            else:
                # New language detected in auto mode
                # Pair with most common language in history or language_a
                if self.detection_history:
                    # Find most common language in recent history
                    recent_langs = [d['lang'] for d in list(self.detection_history)[-10:]]
                    from collections import Counter
                    most_common = Counter(recent_langs).most_common(2)
                    
                    # Use the other most common language
                    for lang, _ in most_common:
                        if lang != source_normalized:
                            return lang
                
                # Default to language_a
                return self.language_a
        else:
            # Standard bidirectional mode
            if source_normalized == lang_a_normalized:
                return self.language_b
            elif source_normalized == lang_b_normalized:
                return self.language_a
            else:
                # Unknown language in non-auto mode
                # Default to the less frequently used language
                # Count recent occurrences
                recent_a = sum(1 for d in self.detection_history if d['lang'][:2] == lang_a_normalized)
                recent_b = sum(1 for d in self.detection_history if d['lang'][:2] == lang_b_normalized)
                
                # Return the language that's been detected less
                return self.language_b if recent_a >= recent_b else self.language_a
    
    def get_status_message(self) -> str:
        """Get current conversation mode status for UI display"""
        if not self.enabled:
            return "Conversation Mode: Disabled"
        
        mode_type = "Auto" if self.auto_mode else "Bidirectional"
        
        if self.auto_mode and len(self.detected_languages) > 2:
            langs = ", ".join(sorted(self.detected_languages))
            return f"🗣️ Conversation Mode (Auto): {langs}"
        else:
            return f"🗣️ Conversation Mode ({mode_type}): {self.language_a} ↔ {self.language_b}"
    
    def get_statistics(self) -> dict:
        """Get conversation statistics for analytics"""
        if not self.detection_history:
            return {
                'total_detections': 0,
                'languages': {},
                'average_confidence': 0.0
            }
        
        from collections import Counter
        
        lang_counts = Counter([d['lang'] for d in self.detection_history])
        avg_confidence = sum(d['confidence'] for d in self.detection_history) / len(self.detection_history)
        
        return {
            'total_detections': len(self.detection_history),
            'languages': dict(lang_counts),
            'average_confidence': avg_confidence,
            'last_detected': self.last_detected_lang,
            'unique_languages': len(self.detected_languages)
        }
    
    def should_translate(self, text: str, detected_lang: str) -> bool:
        """
        Determine if text should be translated based on conversation mode rules
        
        Returns:
            True if translation should proceed, False if text is already in target language
        """
        if not self.enabled:
            return True
        
        # Always translate if we have a valid source and target
        target_lang = self._determine_target_language(detected_lang)
        
        # Don't translate if source and target are the same
        return detected_lang.lower()[:2] != target_lang.lower()[:2]
    
    def update_languages(self, lang_a: str, lang_b: str):
        """Update the language pair for conversation mode"""
        self.language_a = lang_a
        self.language_b = lang_b
        log.info(f"Conversation mode languages updated: {lang_a} ↔ {lang_b}")


# Global instance
conversation_mode = ConversationMode()
