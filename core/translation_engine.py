"""Translation engine with multi-level caching"""
import time
import logging
from concurrent.futures import ThreadPoolExecutor
from deep_translator import GoogleTranslator
import argostranslate.translate
from database import db
from config import config
from utils.helpers import is_online

log = logging.getLogger("Translator")

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

# Global instance
translator = TranslationEngine()
