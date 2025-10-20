"""Configuration management for the translator"""
import json
import threading
import logging
from .constants import CONFIG_FILE, DEFAULT_CONFIG

log = logging.getLogger("Translator")

class ConfigManager:
    """Manages application configuration with thread-safe operations"""
    def __init__(self):
        self.config = self.load_config()
        self.lock = threading.Lock()
    
    def load_config(self) -> dict:
        """Load configuration from file or return defaults"""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, 'r') as f:
                    return {**DEFAULT_CONFIG, **json.load(f)}
            except Exception as e:
                log.warning(f"Failed to load config: {e}")
        return DEFAULT_CONFIG.copy()
    
    def save_config(self):
        """Save current configuration to file"""
        with self.lock:
            try:
                with open(CONFIG_FILE, 'w') as f:
                    json.dump(self.config, f, indent=2)
            except Exception as e:
                log.error(f"Save config failed: {e}")
    
    def get(self, key: str, default=None):
        """Get configuration value thread-safely"""
        with self.lock:
            return self.config.get(key, default)
    
    def set(self, key: str, value):
        """Set configuration value and save"""
        with self.lock:
            self.config[key] = value
        self.save_config()
