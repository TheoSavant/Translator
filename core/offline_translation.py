"""Enhanced Offline Translation with Multiple Backends"""
import logging
import os
from typing import Optional, Tuple
from pathlib import Path
import argostranslate.translate
import argostranslate.package

log = logging.getLogger("Translator")

class EnhancedOfflineTranslation:
    """
    Enhanced offline translation with better model management and caching
    """
    
    def __init__(self):
        self.available_packages = {}
        self.installed_packages = set()
        self.offline_cache = {}  # Additional memory cache for offline translations
        self.max_cache_size = 500
        
        # Initialize Argos Translate
        self._initialize_argos()
    
    def _initialize_argos(self):
        """Initialize Argos Translate and check for installed packages"""
        try:
            # Update package index
            argostranslate.package.update_package_index()
            
            # Get available packages
            available_packages = argostranslate.package.get_available_packages()
            
            for pkg in available_packages:
                key = f"{pkg.from_code}-{pkg.to_code}"
                self.available_packages[key] = pkg
            
            # Check installed packages
            installed_packages = argostranslate.package.get_installed_packages()
            for pkg in installed_packages:
                key = f"{pkg.from_code}-{pkg.to_code}"
                self.installed_packages.add(key)
            
            log.info(f"Argos Translate initialized. Installed packages: {len(self.installed_packages)}")
            
        except Exception as e:
            log.error(f"Failed to initialize Argos Translate: {e}")
    
    def install_language_pair(self, from_lang: str, to_lang: str) -> bool:
        """
        Install a language pair for offline translation
        
        Args:
            from_lang: Source language code (e.g., 'en')
            to_lang: Target language code (e.g., 'fr')
        
        Returns:
            True if installation successful, False otherwise
        """
        key = f"{from_lang}-{to_lang}"
        
        if key in self.installed_packages:
            log.info(f"Language pair {key} already installed")
            return True
        
        if key not in self.available_packages:
            log.warning(f"Language pair {key} not available for installation")
            return False
        
        try:
            package = self.available_packages[key]
            log.info(f"Installing offline translation package: {key}")
            argostranslate.package.install_from_path(package.download())
            self.installed_packages.add(key)
            log.info(f"Successfully installed {key}")
            return True
        except Exception as e:
            log.error(f"Failed to install language pair {key}: {e}")
            return False
    
    def is_language_pair_available(self, from_lang: str, to_lang: str) -> bool:
        """Check if a language pair is available for offline translation"""
        # Direct translation
        direct_key = f"{from_lang}-{to_lang}"
        if direct_key in self.installed_packages:
            return True
        
        # Check for pivot translation (via English)
        if from_lang != 'en' and to_lang != 'en':
            via_english = (f"{from_lang}-en" in self.installed_packages and 
                          f"en-{to_lang}" in self.installed_packages)
            if via_english:
                return True
        
        return False
    
    def translate_offline(self, text: str, from_lang: str, to_lang: str) -> Tuple[Optional[str], float]:
        """
        Translate text using offline models
        
        Args:
            text: Text to translate
            from_lang: Source language code
            to_lang: Target language code
        
        Returns:
            (translated_text, confidence) or (None, 0.0) if translation fails
        """
        if not text or not text.strip():
            return None, 0.0
        
        # Check cache first
        cache_key = f"{text}:{from_lang}:{to_lang}"
        if cache_key in self.offline_cache:
            log.debug("Offline cache hit")
            return self.offline_cache[cache_key], 1.0
        
        try:
            # Try direct translation
            direct_key = f"{from_lang}-{to_lang}"
            
            if direct_key in self.installed_packages:
                translated = argostranslate.translate.translate(text, from_lang, to_lang)
                confidence = 0.85  # Offline translation confidence
                
                # Cache the result
                self._add_to_cache(cache_key, translated)
                
                return translated, confidence
            
            # Try pivot translation through English
            elif from_lang != 'en' and to_lang != 'en':
                key1 = f"{from_lang}-en"
                key2 = f"en-{to_lang}"
                
                if key1 in self.installed_packages and key2 in self.installed_packages:
                    log.debug(f"Using pivot translation: {from_lang} -> en -> {to_lang}")
                    
                    # Translate to English first
                    english_text = argostranslate.translate.translate(text, from_lang, 'en')
                    
                    # Then translate to target language
                    translated = argostranslate.translate.translate(english_text, 'en', to_lang)
                    confidence = 0.75  # Lower confidence for pivot translation
                    
                    # Cache the result
                    self._add_to_cache(cache_key, translated)
                    
                    return translated, confidence
            
            log.warning(f"No offline translation available for {from_lang} -> {to_lang}")
            return None, 0.0
            
        except Exception as e:
            log.error(f"Offline translation failed: {e}")
            return None, 0.0
    
    def _add_to_cache(self, key: str, value: str):
        """Add translation to offline cache with size management"""
        if len(self.offline_cache) >= self.max_cache_size:
            # Remove oldest 20% of entries
            keys_to_remove = list(self.offline_cache.keys())[:self.max_cache_size // 5]
            for k in keys_to_remove:
                del self.offline_cache[k]
        
        self.offline_cache[key] = value
    
    def get_installed_pairs(self) -> list:
        """Get list of installed language pairs"""
        return sorted(list(self.installed_packages))
    
    def get_available_pairs(self) -> list:
        """Get list of available (but not necessarily installed) language pairs"""
        return sorted(list(self.available_packages.keys()))
    
    def auto_install_common_pairs(self, languages: list = None):
        """
        Automatically install common language pairs for better offline support
        
        Args:
            languages: List of language codes to install pairs for (default: common languages)
        """
        if languages is None:
            # Most common languages
            languages = ['en', 'es', 'fr', 'de', 'it', 'pt', 'ru', 'zh', 'ja', 'ko', 'ar']
        
        installed_count = 0
        
        # Install pairs with English as pivot
        for lang in languages:
            if lang != 'en':
                # Install both directions
                if self.install_language_pair(lang, 'en'):
                    installed_count += 1
                if self.install_language_pair('en', lang):
                    installed_count += 1
        
        log.info(f"Auto-installed {installed_count} language pairs for offline support")
        return installed_count
    
    def get_status_info(self) -> dict:
        """Get status information about offline translation"""
        return {
            'installed_pairs': len(self.installed_packages),
            'available_pairs': len(self.available_packages),
            'cache_size': len(self.offline_cache),
            'installed_list': self.get_installed_pairs()
        }
    
    def clear_cache(self):
        """Clear the offline translation cache"""
        self.offline_cache.clear()
        log.info("Offline translation cache cleared")


# Global instance
offline_translator = EnhancedOfflineTranslation()
