"""Audio device detection and management"""
import logging
import pyaudio
import sounddevice as sd
from dataclasses import dataclass
from typing import List, Optional

log = logging.getLogger("Translator")

@dataclass
class AudioDevice:
    """Represents an audio device"""
    index: int
    name: str
    max_input_channels: int
    max_output_channels: int
    default_samplerate: float
    is_input: bool
    is_output: bool
    host_api: str

class AudioDeviceManager:
    """Manages audio device detection and selection"""
    def __init__(self):
        self.pa = pyaudio.PyAudio()
        self.devices = self._detect_devices()
        self.input_devices = [d for d in self.devices if d.is_input]
    
    def _detect_devices(self) -> List[AudioDevice]:
        """Detect all available audio devices"""
        devices = []
        try:
            for i in range(self.pa.get_device_count()):
                info = self.pa.get_device_info_by_index(i)
                device = AudioDevice(
                    index=i,
                    name=info['name'],
                    max_input_channels=info['maxInputChannels'],
                    max_output_channels=info['maxOutputChannels'],
                    default_samplerate=info['defaultSampleRate'],
                    is_input=info['maxInputChannels'] > 0,
                    is_output=info['maxOutputChannels'] > 0,
                    host_api=self.pa.get_host_api_info_by_index(info['hostApi'])['name']
                )
                devices.append(device)
        except Exception as e:
            log.error(f"Error detecting devices: {e}")
        return devices
    
    def get_default_input_device(self) -> Optional[AudioDevice]:
        """Get the default input device"""
        try:
            default_info = self.pa.get_default_input_device_info()
            for device in self.input_devices:
                if device.index == default_info['index']:
                    return device
        except:
            pass
        return self.input_devices[0] if self.input_devices else None
    
    def get_loopback_device(self) -> Optional[AudioDevice]:
        """Get loopback device with validation"""
        keywords = ['stereo mix', 'loopback', 'wave out', 'what u hear', 'wave-out', 'waveout']
        candidates = []
        
        # Find all potential loopback devices
        for device in self.input_devices:
            device_name_lower = device.name.lower()
            if any(k in device_name_lower for k in keywords):
                candidates.append(device)
        
        # Try to find a working device by testing each candidate
        for device in candidates:
            try:
                # Quick test with sounddevice
                test_stream = sd.InputStream(
                    channels=1,
                    samplerate=int(device.default_samplerate),
                    device=device.index,
                    blocksize=1024
                )
                test_stream.close()
                log.info(f"Found working loopback device: {device.name}")
                return device
            except Exception as e:
                log.warning(f"Loopback device {device.name} failed test: {e}")
                continue
        
        # If no keywords match, try the default input device if it's not a microphone
        try:
            default = self.get_default_input_device()
            if default and 'mic' not in default.name.lower():
                log.info(f"Trying default input as loopback: {default.name}")
                return default
        except Exception as e:
            log.warning(f"Default device check failed: {e}")
        
        return None
    
    def test_device(self, device: AudioDevice, duration: float = 1.0) -> bool:
        """Test if a device is working"""
        try:
            stream = self.pa.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=int(device.default_samplerate),
                input=True,
                input_device_index=device.index,
                frames_per_buffer=1024
            )
            stream.read(int(device.default_samplerate * duration))
            stream.stop_stream()
            stream.close()
            return True
        except:
            return False
    
    def cleanup(self):
        """Clean up PyAudio resources"""
        self.pa.terminate()

# Global instance
audio_device_manager = AudioDeviceManager()
