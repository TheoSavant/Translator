"""Translation engine with multi-level caching and contextual awareness"""
import time
import logging
from concurrent.futures import ThreadPoolExecutor
from deep_translator import GoogleTranslator
import argostranslate.translate
from database import db
from config import config
from utils.helpers import is_online
from .contextual_engine import contextual_engine
from .conversation_mode import conversation_mode
from .offline_translation import offline_translator

log = logging.getLogger("Translator")

class TranslationEngine:
    """Professional translation engine with enhanced caching, contextual awareness, and conversation mode"""
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=6, thread_name_prefix="TranslateWorker")
        # In-memory cache for ultra-fast repeated translations
        self.memory_cache = {}
        self.cache_hits = 0
        self.cache_misses = 0
        
        # Contextual features
        self.use_contextual = True
        self.use_slang_expansion = True
        self.use_autocorrect = True
    
    def translate(self, text, src, tgt, use_conversation_mode=True):
        """
        Translate with enhanced multi-level caching, contextual awareness, and conversation mode
        
        Args:
            text: Text to translate
            src: Source language (can be "auto" for auto-detection)
            tgt: Target language
            use_conversation_mode: Whether to use conversation mode for auto-routing
        
        Returns:
            (translated_text, duration_ms, confidence)
        """
        if not text.strip():
            return "", 0, 1.0
        
        original_text = text
        original_src = src
        original_tgt = tgt
        
        # Step 1: Conversation Mode - Auto-detect and route languages
        if use_conversation_mode and conversation_mode.enabled:
            src, tgt, conv_confidence = conversation_mode.get_target_language(text, src if src != "auto" else None)
            log.debug(f"Conversation mode routing: {src} → {tgt}")
        
        # Step 2: Contextual preprocessing
        if self.use_autocorrect and src != "auto":
            # Apply contextual autocorrect and slang expansion
            text = contextual_engine.autocorrect_with_context(text, src)
            
            if self.use_slang_expansion:
                text, was_expanded = contextual_engine.expand_slang(text, src)
                if was_expanded:
                    log.debug(f"Slang expanded: {original_text} → {text}")
        
        # Step 3: Check caches
        # Level 1: In-memory cache (ultra-fast, ~0ms)
        cache_key = f"{text}:{src}:{tgt}"
        if cache_key in self.memory_cache:
            self.cache_hits += 1
            cached_result = self.memory_cache[cache_key]
            log.debug(f"Memory cache HIT ({self.cache_hits}/{self.cache_hits + self.cache_misses})")
            
            # Apply contextual enhancement even to cached results
            enhanced = cached_result[0]
            if self.use_contextual:
                enhanced = contextual_engine.enhance_translation_with_context(
                    original_text, enhanced, src, tgt
                )
            
            return enhanced, 0, cached_result[1]
        
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
                
                # Apply contextual enhancement
                enhanced = cached
                if self.use_contextual:
                    enhanced = contextual_engine.enhance_translation_with_context(
                        original_text, enhanced, src, tgt
                    )
                
                return enhanced, 0, 1.0
        
        # Step 4: Perform translation
        self.cache_misses += 1
        start = time.time()
        translated = None
        confidence = 1.0
        
        # Try online translation first (Google Translate)
        if is_online():
            try:
                translated = GoogleTranslator(source=src, target=tgt).translate(text)
                confidence = 1.0
                log.debug(f"Google Translate success: {text[:50]} → {translated[:50]}")
            except Exception as e:
                log.warning(f"Google Translate failed: {e}")
        
        # Fallback to enhanced offline translation
        if not translated:
            try:
                # Use enhanced offline translator with better model management
                translated, confidence = offline_translator.translate_offline(text, src, tgt)
                
                if not translated:
                    # Final fallback to basic Argos
                    translated = argostranslate.translate.translate(text, from_code=src, to_code=tgt)
                    confidence = 0.85
                    
                log.debug(f"Offline translation used (confidence: {confidence})")
            except Exception as e:
                log.warning(f"Offline translation failed: {e}")
                translated = text
                confidence = 0.0
        
        duration = int((time.time() - start) * 1000)
        
        # Step 5: Contextual enhancement of translation
        if translated and self.use_contextual:
            translated = contextual_engine.enhance_translation_with_context(
                original_text, translated, src, tgt
            )
            
            # Add to context history for future reference
            contextual_engine.add_context(original_text, src)
        
        # Step 6: Cache the result in both levels
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

# Global instance
translator = TranslationEngine()
