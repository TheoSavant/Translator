"""GPU detection and management"""
import logging
import torch

log = logging.getLogger("Translator")

class GPUManager:
    """Manages GPU detection and device selection for PyTorch"""
    def __init__(self):
        # Enhanced CUDA detection
        self.has_cuda = torch.cuda.is_available()
        if not self.has_cuda and torch.version.cuda is not None:
            # Try to initialize CUDA even if not initially available
            try:
                torch.cuda.init()
                self.has_cuda = torch.cuda.is_available()
            except:
                pass
        
        self.has_mps = hasattr(torch.backends, 'mps') and torch.backends.mps.is_available()
        self.device = self._detect_device()
        self.device_name = self._get_device_name()
        
        # Log detailed GPU info
        if self.has_cuda:
            log.info(f"CUDA detected: {torch.cuda.get_device_name(0)}")
            log.info(f"CUDA version: {torch.version.cuda}")
            log.info(f"CUDA device count: {torch.cuda.device_count()}")
        else:
            log.warning("CUDA not detected. GPU acceleration disabled.")
            if torch.version.cuda:
                log.warning(f"PyTorch built with CUDA {torch.version.cuda} but CUDA runtime not available")
    
    def _detect_device(self):
        """Detect available compute device"""
        if self.has_cuda:
            return "cuda"
        elif self.has_mps:
            return "mps"
        return "cpu"
    
    def _get_device_name(self):
        """Get human-readable device name"""
        if self.has_cuda:
            return f"CUDA ({torch.cuda.get_device_name(0)})"
        elif self.has_mps:
            return "Apple Silicon (MPS)"
        return "CPU"
    
    def get_device(self, use_gpu=True):
        """Get device string for PyTorch operations"""
        if use_gpu and (self.has_cuda or self.has_mps):
            return self.device
        return "cpu"
    
    def is_gpu_available(self):
        """Check if any GPU is available"""
        return self.has_cuda or self.has_mps

# Global instance
gpu_manager = GPUManager()
