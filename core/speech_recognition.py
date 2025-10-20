"""Continuous speech recognition with multiple engine support"""
import time
import json
import queue
import threading
import logging
import numpy as np
from collections import deque
from concurrent.futures import ThreadPoolExecutor
import speech_recognition as sr
import sounddevice as sd
from vosk import KaldiRecognizer
from PyQt6.QtCore import QThread, pyqtSignal
from config import config
from config.constants import RecognitionEngine
from models import vosk_manager, whisper_manager
from utils import audio_device_manager
from utils.helpers import is_online

log = logging.getLogger("Translator")

class ContinuousSpeechRecognitionThread(QThread):
    """Continuous listening - never stops, async processing"""
    phrase_detected = pyqtSignal(str, float)
    status_changed = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    performance_update = pyqtSignal(dict)  # Queue sizes, processing time
    
    def __init__(self, source_type="microphone", language="en", 
                 engine=RecognitionEngine.GOOGLE, device_index=None):
        super().__init__()
        self.running = True
        self.source_type = source_type
        self.language = language
        self.engine = engine
        self.device_index = device_index
        self.vosk_model = vosk_manager.get_model(language) if engine == RecognitionEngine.VOSK else None
        self.whisper_model_size = config.get("whisper_model", "base")
        
        # Processing queues for async pipeline
        self.recognition_queue = queue.Queue(maxsize=10)  # Audio chunks waiting for recognition
        self.translation_queue = queue.Queue(maxsize=10)  # Texts waiting for translation
        
        # Thread pool for parallel processing
        self.executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="RecognitionWorker")
        self.executor_shutdown = False
        
        # Performance monitoring
        self.processing_times = deque(maxlen=20)
        self.last_perf_update = time.time()
    
    def run(self):
        """Main thread entry point"""
        try:
            if self.source_type == "microphone":
                self._listen_microphone_continuous()
            else:
                self._listen_system_audio_continuous()
        except Exception as e:
            self.error_occurred.emit(f"Recognition error: {e}")
    
    def _listen_microphone_continuous(self):
        """Continuous microphone listening - never stops"""
        recognizer = sr.Recognizer()
        recognizer.energy_threshold = 3000
        recognizer.pause_threshold = 1.2
        
        try:
            kwargs = {}
            if self.device_index is not None:
                kwargs['device_index'] = self.device_index
            
            with sr.Microphone(**kwargs) as source:
                self.status_changed.emit("🎙️ Calibrating...")
                recognizer.adjust_for_ambient_noise(source, 1)
                self.status_changed.emit(f"🎙️ Continuous Listening ({self.engine.value})...")
                
                while self.running:
                    try:
                        # Non-blocking listen - captures audio continuously
                        audio = recognizer.listen(source, timeout=None, phrase_time_limit=15)
                        
                        # Async processing - submit to queue
                        if not self.recognition_queue.full() and not self.executor_shutdown:
                            self.executor.submit(self._process_audio, audio)
                        elif self.executor_shutdown:
                            break
                        else:
                            log.warning("Recognition queue full, dropping audio")
                        
                        # Update performance metrics
                        self._update_performance()
                        
                    except sr.WaitTimeoutError:
                        pass
                    except Exception as e:
                        if self.running:  # Only log if we're supposed to be running
                            log.warning(f"Mic error: {e}")
                        time.sleep(0.5)
        except Exception as e:
            if self.running:
                self.error_occurred.emit(f"Microphone setup failed: {e}")
    
    def _listen_system_audio_continuous(self):
        """Continuous system audio capture with proper threading and validation"""
        loopback = audio_device_manager.get_loopback_device()
        if not loopback:
            error_msg = (
                "❌ No working loopback device found.\n\n"
                "Windows: Enable 'Stereo Mix' in Sound Settings:\n"
                "  1. Right-click speaker icon → Sounds\n"
                "  2. Recording tab → Right-click → Show Disabled Devices\n"
                "  3. Enable 'Stereo Mix' or 'Wave Out Mix'\n\n"
                "macOS: Install BlackHole or Soundflower\n\n"
                "Linux: Use PulseAudio monitor device"
            )
            self.error_occurred.emit(error_msg)
            return
        
        # Validate sample rate
        try:
            samplerate = int(loopback.default_samplerate)
            if samplerate > 48000:
                log.warning(f"Sample rate {samplerate} too high, limiting to 16000")
                samplerate = 16000
            elif samplerate < 8000:
                log.warning(f"Sample rate {samplerate} too low, using 16000")
                samplerate = 16000
            else:
                samplerate = min(samplerate, 16000)
        except Exception as e:
            log.error(f"Sample rate validation failed: {e}")
            samplerate = 16000
        
        audio_buffer = []
        samples_needed = int(samplerate * 5.0)
        buffer_lock = threading.Lock()
        stream_error = [None]  # Use list to allow modification in callback
        
        def callback(indata, frames, time_info, status):
            """Audio callback - runs in separate thread"""
            try:
                if status:
                    log.warning(f"Audio callback status: {status}")
                
                if not self.running:
                    raise sd.CallbackStop()
                
                # Validate input data
                if indata is None or len(indata) == 0:
                    return
                
                with buffer_lock:
                    # Handle mono/stereo input
                    if indata.ndim == 1:
                        audio_buffer.extend(indata.copy())
                    else:
                        audio_buffer.extend(indata[:, 0].copy())
                    
                    if len(audio_buffer) >= samples_needed:
                        chunk = np.array(audio_buffer[:samples_needed])
                        audio_buffer.clear()
                        
                        # Submit to thread pool for processing
                        if not self.recognition_queue.full() and not self.executor_shutdown:
                            try:
                                self.executor.submit(self._process_system_audio, chunk, samplerate)
                            except Exception as e:
                                if self.running:
                                    log.error(f"Failed to submit audio processing: {e}")
            except sd.CallbackStop:
                raise
            except Exception as e:
                stream_error[0] = str(e)
                log.error(f"Audio callback error: {e}")
                raise sd.CallbackStop()
        
        try:
            log.info(f"Opening system audio stream: device={loopback.name}, rate={samplerate}, index={loopback.index}")
            self.status_changed.emit(f"🎧 Capturing system audio ({self.engine.value})...")
            
            # Test device access before starting stream
            try:
                test_stream = sd.InputStream(
                    channels=1,
                    samplerate=samplerate,
                    device=loopback.index,
                    blocksize=1024
                )
                test_stream.close()
                log.info("Device test successful")
            except Exception as test_error:
                error_msg = (
                    f"❌ System audio device test failed:\n\n"
                    f"Device: {loopback.name}\n"
                    f"Error: {test_error}\n\n"
                    f"The device may be in use by another application\n"
                    f"or not properly configured for recording."
                )
                self.error_occurred.emit(error_msg)
                return
            
            # Start actual capture stream
            with sd.InputStream(
                channels=1, 
                samplerate=samplerate, 
                device=loopback.index, 
                callback=callback, 
                blocksize=4096
            ):
                while self.running:
                    if stream_error[0]:
                        raise RuntimeError(stream_error[0])
                    sd.sleep(100)
                    self._update_performance()
                    
        except Exception as e:
            if self.running:
                import traceback
                error_details = traceback.format_exc()
                log.error(f"System audio error:\n{error_details}")
                
                error_msg = (
                    f"❌ System audio failed:\n\n"
                    f"Error: {str(e)}\n\n"
                    f"Device: {loopback.name if loopback else 'Unknown'}\n\n"
                    f"Possible solutions:\n"
                    f"• Close other apps using the audio device\n"
                    f"• Check device is enabled in system settings\n"
                    f"• Try restarting the application\n"
                    f"• Use Microphone mode instead"
                )
                self.error_occurred.emit(error_msg)
    
    def _process_audio(self, audio):
        """Process audio chunk - runs in thread pool"""
        start_time = time.time()
        try:
            text, conf = None, 1.0
            
            if self.engine == RecognitionEngine.WHISPER:
                text, conf = self._recognize_whisper(audio)
            elif self.engine == RecognitionEngine.VOSK and self.vosk_model:
                text, conf = self._recognize_vosk(audio.get_wav_data())
            elif self.engine == RecognitionEngine.GOOGLE:
                if is_online():
                    try:
                        text = sr.Recognizer().recognize_google(audio, language=self.language)
                    except:
                        pass
            
            if text and text.strip():
                self.phrase_detected.emit(text, conf)
            
            # Track processing time
            elapsed = (time.time() - start_time) * 1000
            self.processing_times.append(elapsed)
            
        except Exception as e:
            log.error(f"Process audio error: {e}")
    
    def _process_system_audio(self, audio_data, samplerate):
        """Process system audio chunk"""
        if not self.running or self.executor_shutdown:
            return
        
        start_time = time.time()
        try:
            energy = np.sqrt(np.mean(audio_data ** 2))
            if energy < 0.01:
                return
            
            text, conf = "", 0.0
            if self.engine == RecognitionEngine.WHISPER:
                text, conf = self._transcribe_whisper_array(audio_data, samplerate)
            elif self.engine == RecognitionEngine.VOSK and self.vosk_model:
                audio_int = (audio_data * 32767).astype(np.int16)
                text, conf = self._recognize_vosk(audio_int.tobytes())
            
            if text and text.strip():
                self.phrase_detected.emit(text, conf)
            
            elapsed = (time.time() - start_time) * 1000
            self.processing_times.append(elapsed)
            
        except Exception as e:
            if self.running:
                log.error(f"Process system audio error: {e}")
    
    def _recognize_vosk(self, wav_data):
        """Recognize speech using Vosk"""
        if not self.vosk_model:
            return "", 0.0
        try:
            rec = KaldiRecognizer(self.vosk_model, 16000)
            rec.SetWords(True)
            rec.AcceptWaveform(wav_data)
            result = json.loads(rec.FinalResult())
            return result.get("text", ""), result.get("confidence", 0.9)
        except:
            return "", 0.0
    
    def _recognize_whisper(self, audio):
        """Recognize speech using Whisper"""
        try:
            audio_np = np.frombuffer(audio.get_wav_data(), dtype=np.int16).astype(np.float32) / 32768.0
            if audio.sample_rate != 16000:
                from scipy import signal
                audio_np = signal.resample(audio_np, int(len(audio_np) * 16000 / audio.sample_rate))
            lang = self.language if self.language != "auto" else None
            return whisper_manager.transcribe(audio_np, self.whisper_model_size, lang)
        except:
            return "", 0.0
    
    def _transcribe_whisper_array(self, audio_data, samplerate):
        """Transcribe audio array using Whisper"""
        try:
            if samplerate != 16000:
                from scipy import signal
                audio_data = signal.resample(audio_data, int(len(audio_data) * 16000 / samplerate))
            lang = self.language if self.language != "auto" else None
            return whisper_manager.transcribe(audio_data, self.whisper_model_size, lang)
        except:
            return "", 0.0
    
    def _update_performance(self):
        """Update performance metrics periodically"""
        now = time.time()
        if now - self.last_perf_update > 1.0:  # Update every second
            avg_time = sum(self.processing_times) / len(self.processing_times) if self.processing_times else 0
            perf_data = {
                'recognition_queue': self.recognition_queue.qsize(),
                'translation_queue': self.translation_queue.qsize(),
                'avg_processing_time': avg_time,
                'device': whisper_manager.device if self.engine == RecognitionEngine.WHISPER else 'N/A'
            }
            self.performance_update.emit(perf_data)
            self.last_perf_update = now
    
    def stop(self):
        """Stop the recognition thread"""
        self.running = False
        self.executor_shutdown = True
        # Shutdown executor gracefully
        self.executor.shutdown(wait=False)
