"""Vosk speech recognition model management"""
import logging
import requests
from pathlib import Path
from vosk import Model
from config.constants import VOSK_MODELS, VOSK_MODELS_DIR

log = logging.getLogger("Translator")

class VoskModelManager:
    """Manages Vosk model downloading and loading"""
    def __init__(self):
        self.models = {}
        self.load_existing_models()
    
    def load_existing_models(self):
        """Load already downloaded Vosk models"""
        for lang_code in VOSK_MODELS.keys():
            model_dir = VOSK_MODELS_DIR / f"vosk-model-small-{lang_code}"
            if model_dir.exists():
                try:
                    self.models[lang_code] = Model(str(model_dir))
                    log.info(f"Loaded Vosk model for {lang_code}")
                except Exception as e:
                    log.warning(f"Failed to load Vosk model for {lang_code}: {e}")
    
    def get_model(self, lang_code):
        """Get a loaded model by language code"""
        return self.models.get(lang_code)
    
    def download_model(self, lang_code, progress_callback=None):
        """Download and install a Vosk model"""
        if lang_code not in VOSK_MODELS:
            return False
        model_dir = VOSK_MODELS_DIR / f"vosk-model-small-{lang_code}"
        if model_dir.exists():
            return True
        try:
            url = VOSK_MODELS[lang_code]
            zip_path = VOSK_MODELS_DIR / f"model-{lang_code}.zip"
            response = requests.get(url, stream=True)
            total = int(response.headers.get('content-length', 0))
            downloaded = 0
            with open(zip_path, 'wb') as f:
                for chunk in response.iter_content(8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if progress_callback and total > 0:
                            progress_callback(downloaded / total)
            import zipfile
            with zipfile.ZipFile(zip_path, 'r') as z:
                z.extractall(VOSK_MODELS_DIR)
            zip_path.unlink()
            for item in VOSK_MODELS_DIR.iterdir():
                if item.is_dir() and lang_code in item.name.lower():
                    if item.name != f"vosk-model-small-{lang_code}":
                        item.rename(model_dir)
                    break
            self.models[lang_code] = Model(str(model_dir))
            return True
        except Exception as e:
            log.error(f"Download failed: {e}")
            return False
    
    def has_model(self, lang_code):
        """Check if a model is loaded"""
        return lang_code in self.models

# Global instance
vosk_manager = VoskModelManager()
