"""RVC (Voice Duplication) Model Manager for Custom TTS"""
import os
import logging
import shutil
from pathlib import Path
from typing import Optional, Dict, List, Tuple
import json
from config.constants import BASE_DIR

log = logging.getLogger("Translator")

# RVC models directory
RVC_MODELS_DIR = BASE_DIR / "rvc_models"
RVC_MODELS_DIR.mkdir(parents=True, exist_ok=True)

class RVCModelManager:
    """Manages RVC voice cloning models for voice duplication mode"""
    
    def __init__(self):
        self.models_dir = RVC_MODELS_DIR
        self.models = {}
        self.current_model = None
        self.load_models()
    
    def load_models(self):
        """Load all available RVC models from the models directory"""
        self.models = {}
        
        if not self.models_dir.exists():
            self.models_dir.mkdir(parents=True, exist_ok=True)
            return
        
        # Scan for model directories
        for model_dir in self.models_dir.iterdir():
            if model_dir.is_dir():
                model_info = self._scan_model_directory(model_dir)
                if model_info:
                    self.models[model_dir.name] = model_info
                    log.info(f"Loaded RVC model: {model_dir.name}")
        
        log.info(f"Total RVC models loaded: {len(self.models)}")
    
    def _scan_model_directory(self, model_dir: Path) -> Optional[Dict]:
        """Scan a model directory for RVC files"""
        model_info = {
            'name': model_dir.name,
            'path': str(model_dir),
            'pth_file': None,
            'index_file': None,
            'config_file': None,
            'other_files': []
        }
        
        # Look for specific file types
        for file in model_dir.iterdir():
            if file.is_file():
                suffix = file.suffix.lower()
                
                if suffix == '.pth':
                    model_info['pth_file'] = str(file)
                elif suffix == '.index':
                    model_info['index_file'] = str(file)
                elif suffix in ['.json', '.yaml', '.yml'] and 'config' in file.name.lower():
                    model_info['config_file'] = str(file)
                else:
                    model_info['other_files'].append(str(file))
        
        # Valid model must have at least a PTH file
        if model_info['pth_file']:
            return model_info
        return None
    
    def add_model(self, model_name: str, files: Dict[str, str]) -> bool:
        """
        Add a new RVC model from uploaded files
        
        Args:
            model_name: Name for the model
            files: Dict with keys 'pth', 'index', 'config', etc. and file paths as values
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create model directory
            model_dir = self.models_dir / model_name
            model_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy files to model directory
            for file_type, file_path in files.items():
                if file_path and os.path.exists(file_path):
                    dest_path = model_dir / os.path.basename(file_path)
                    shutil.copy2(file_path, dest_path)
                    log.info(f"Copied {file_type} file: {os.path.basename(file_path)}")
            
            # Reload models
            self.load_models()
            log.info(f"Successfully added RVC model: {model_name}")
            return True
            
        except Exception as e:
            log.error(f"Failed to add RVC model: {e}")
            return False
    
    def remove_model(self, model_name: str) -> bool:
        """Remove an RVC model"""
        try:
            model_dir = self.models_dir / model_name
            if model_dir.exists():
                shutil.rmtree(model_dir)
                self.load_models()
                log.info(f"Removed RVC model: {model_name}")
                return True
            return False
        except Exception as e:
            log.error(f"Failed to remove RVC model: {e}")
            return False
    
    def get_model_info(self, model_name: str) -> Optional[Dict]:
        """Get information about a specific model"""
        return self.models.get(model_name)
    
    def list_models(self) -> List[str]:
        """List all available model names"""
        return list(self.models.keys())
    
    def set_current_model(self, model_name: str) -> bool:
        """Set the current active model for voice duplication"""
        if model_name in self.models:
            self.current_model = model_name
            log.info(f"Active RVC model set to: {model_name}")
            return True
        return False
    
    def get_current_model(self) -> Optional[str]:
        """Get the name of the current active model"""
        return self.current_model
    
    def get_current_model_info(self) -> Optional[Dict]:
        """Get full info of the current active model"""
        if self.current_model:
            return self.models.get(self.current_model)
        return None
    
    def validate_model(self, model_name: str) -> Tuple[bool, str]:
        """
        Validate if a model has all necessary files
        
        Returns:
            (is_valid, message)
        """
        if model_name not in self.models:
            return False, "Model not found"
        
        model_info = self.models[model_name]
        
        if not model_info['pth_file']:
            return False, "Missing PTH file (required)"
        
        warnings = []
        if not model_info['index_file']:
            warnings.append("No index file (recommended for better quality)")
        if not model_info['config_file']:
            warnings.append("No config file (may use defaults)")
        
        if warnings:
            return True, "Valid with warnings: " + "; ".join(warnings)
        
        return True, "Model is complete and ready"
    
    def export_model_list(self) -> str:
        """Export model list as JSON string"""
        export_data = {
            'models': self.models,
            'current_model': self.current_model
        }
        return json.dumps(export_data, indent=2)
    
    def get_model_stats(self) -> Dict:
        """Get statistics about loaded models"""
        return {
            'total_models': len(self.models),
            'models_with_index': sum(1 for m in self.models.values() if m['index_file']),
            'models_with_config': sum(1 for m in self.models.values() if m['config_file']),
            'current_model': self.current_model,
            'models_dir_size_mb': self._get_dir_size_mb()
        }
    
    def _get_dir_size_mb(self) -> float:
        """Calculate total size of models directory in MB"""
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(self.models_dir):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                if os.path.exists(filepath):
                    total_size += os.path.getsize(filepath)
        return round(total_size / (1024 * 1024), 2)


# Global instance
rvc_manager = RVCModelManager()
