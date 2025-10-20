"""Settings dialog for configuring the translator"""
import logging
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from config import config
from config.constants import WHISPER_MODELS, RecognitionEngine, CONFIG_FILE, DB_FILE, AUDIO_DIR, VOSK_MODELS_DIR
from deep_translator.constants import GOOGLE_LANGUAGES_TO_CODES
from models import vosk_manager, whisper_manager
from utils import audio_device_manager, gpu_manager
from core import tts_manager

log = logging.getLogger("Translator")

class SettingsDialog(QDialog):
    """Netflix/Google-level comprehensive settings dialog with Material Design 3 styling"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⚙️ Settings — Universal Live Translator")
        self.setMinimumWidth(700)
        self.setMinimumHeight(750)
        self.setup_ui()
        # Apply professional styling to dialog
        self.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0f0f14, stop:1 #1a1a20);
            }
            QTabWidget::pane {
                border: 1.5px solid rgba(255,255,255,0.08);
                border-radius: 12px;
                background: rgba(42,42,50,0.3);
                padding: 10px;
            }
            QTabBar::tab {
                background: rgba(60,60,70,0.5);
                color: #b8bbbe;
                padding: 10px 20px;
                margin-right: 4px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-weight: 500;
                font-size: 13px;
            }
            QTabBar::tab:selected {
                background: rgba(130,200,255,0.15);
                color: #82c8ff;
                border-bottom: 2px solid #82c8ff;
            }
            QTabBar::tab:hover:!selected {
                background: rgba(75,75,85,0.6);
            }
        """)
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Create tab widget for organized settings
        tabs = QTabWidget()
        
        # ===== GENERAL TAB =====
        general_tab = QWidget()
        general_layout = QVBoxLayout(general_tab)
        
        # Theme
        theme_group = QGroupBox("Appearance")
        theme_layout = QVBoxLayout()
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark", "Light"])
        self.theme_combo.setCurrentText(config.get("theme", "dark").title())
        theme_layout.addWidget(QLabel("Theme:"))
        theme_layout.addWidget(self.theme_combo)
        
        # Font size
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(10, 48)
        self.font_size_spin.setValue(config.get("font_size", 20))
        theme_layout.addWidget(QLabel("Overlay Font Size:"))
        theme_layout.addWidget(self.font_size_spin)
        
        # Text color
        self.text_color_btn = QPushButton("Choose Text Color")
        self.text_color = config.get("text_color", "#FFFFFF")
        self.text_color_btn.clicked.connect(self.choose_text_color)
        theme_layout.addWidget(QLabel("Overlay Text Color:"))
        theme_layout.addWidget(self.text_color_btn)
        
        theme_group.setLayout(theme_layout)
        general_layout.addWidget(theme_group)
        
        # Animation
        anim_group = QGroupBox("Animation")
        anim_layout = QVBoxLayout()
        self.anim_duration_spin = QSpinBox()
        self.anim_duration_spin.setRange(0, 1000)
        self.anim_duration_spin.setValue(config.get("animation_duration", 200))
        self.anim_duration_spin.setSuffix(" ms")
        anim_layout.addWidget(QLabel("Animation Duration:"))
        anim_layout.addWidget(self.anim_duration_spin)
        anim_group.setLayout(anim_layout)
        general_layout.addWidget(anim_group)
        
        # Max words and subtitle settings
        words_group = QGroupBox("Overlay & Subtitle Settings")
        words_layout = QVBoxLayout()
        
        self.max_words_spin = QSpinBox()
        self.max_words_spin.setRange(10, 500)
        self.max_words_spin.setValue(config.get("max_words", 100))
        words_layout.addWidget(QLabel("Maximum Words in Overlay:"))
        words_layout.addWidget(self.max_words_spin)
        
        # Subtitle lines
        self.subtitle_lines_spin = QSpinBox()
        self.subtitle_lines_spin.setRange(1, 10)
        self.subtitle_lines_spin.setValue(config.get("subtitle_lines", 3))
        words_layout.addWidget(QLabel("Number of Subtitle Lines:"))
        words_layout.addWidget(self.subtitle_lines_spin)
        
        # Subtitle update speed
        self.subtitle_delay_spin = QSpinBox()
        self.subtitle_delay_spin.setRange(1, 100)
        self.subtitle_delay_spin.setValue(config.get("subtitle_update_delay", 10))
        self.subtitle_delay_spin.setSuffix(" ms")
        words_layout.addWidget(QLabel("Subtitle Update Speed (lower = faster):"))
        words_layout.addWidget(self.subtitle_delay_spin)
        
        speed_hint = QLabel("💡 Tip: 5-10ms for instant updates, 30-50ms for smoother animation")
        speed_hint.setWordWrap(True)
        speed_hint.setStyleSheet("color: #888; font-size: 11px;")
        words_layout.addWidget(speed_hint)
        
        words_group.setLayout(words_layout)
        general_layout.addWidget(words_group)
        
        general_layout.addStretch()
        tabs.addTab(general_tab, "General")
        
        # ===== AUDIO TAB =====
        audio_tab = QWidget()
        audio_layout = QVBoxLayout(audio_tab)
        
        # TTS Settings
        tts_group = QGroupBox("Text-to-Speech")
        tts_layout = QVBoxLayout()
        
        self.tts_rate_spin = QSpinBox()
        self.tts_rate_spin.setRange(50, 300)
        self.tts_rate_spin.setValue(config.get("tts_rate", 150))
        tts_layout.addWidget(QLabel("Speech Rate:"))
        tts_layout.addWidget(self.tts_rate_spin)
        
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(int(config.get("volume", 0.8) * 100))
        self.volume_label = QLabel(f"{self.volume_slider.value()}%")
        self.volume_slider.valueChanged.connect(lambda v: self.volume_label.setText(f"{v}%"))
        tts_layout.addWidget(QLabel("Volume:"))
        tts_layout.addWidget(self.volume_slider)
        tts_layout.addWidget(self.volume_label)
        
        tts_group.setLayout(tts_layout)
        audio_layout.addWidget(tts_group)
        
        # Audio Device
        device_group = QGroupBox("Audio Input Device")
        device_layout = QVBoxLayout()
        self.device_combo = QComboBox()
        self.device_combo.addItem("Default", "default")
        for device in audio_device_manager.input_devices:
            self.device_combo.addItem(f"{device.name} ({device.host_api})", str(device.index))
        current_device = config.get("audio_device_input", "default")
        idx = self.device_combo.findData(current_device)
        if idx >= 0:
            self.device_combo.setCurrentIndex(idx)
        device_layout.addWidget(QLabel("Input Device:"))
        device_layout.addWidget(self.device_combo)
        device_group.setLayout(device_layout)
        audio_layout.addWidget(device_group)
        
        audio_layout.addStretch()
        tabs.addTab(audio_tab, "Audio")
        
        # ===== GPU/ENGINE TAB =====
        engine_tab = QWidget()
        engine_layout = QVBoxLayout(engine_tab)
        
        # GPU Settings
        gpu_group = QGroupBox("GPU Acceleration")
        gpu_layout = QVBoxLayout()
        
        self.use_gpu_check = QCheckBox("Enable GPU Acceleration (CUDA/MPS)")
        self.use_gpu_check.setChecked(config.get("use_gpu", True))
        self.use_gpu_check.setEnabled(gpu_manager.is_gpu_available())
        gpu_layout.addWidget(self.use_gpu_check)
        
        gpu_info = QLabel(f"Status: {gpu_manager.device_name}")
        gpu_info.setWordWrap(True)
        gpu_layout.addWidget(gpu_info)
        
        if not gpu_manager.is_gpu_available():
            gpu_warning = QLabel("⚠️ No GPU detected. Install CUDA (NVIDIA) or use Apple Silicon for GPU acceleration.")
            gpu_warning.setWordWrap(True)
            gpu_warning.setStyleSheet("color: #FFC107;")
            gpu_layout.addWidget(gpu_warning)
        
        gpu_group.setLayout(gpu_layout)
        engine_layout.addWidget(gpu_group)
        
        # Whisper Model
        whisper_group = QGroupBox("Whisper Model")
        whisper_layout = QVBoxLayout()
        self.whisper_model_combo = QComboBox()
        for model in WHISPER_MODELS:
            self.whisper_model_combo.addItem(model.title(), model)
        current_model = config.get("whisper_model", "base")
        idx = self.whisper_model_combo.findData(current_model)
        if idx >= 0:
            self.whisper_model_combo.setCurrentIndex(idx)
        whisper_layout.addWidget(QLabel("Model Size:"))
        whisper_layout.addWidget(self.whisper_model_combo)
        
        model_info = QLabel(
            "• Tiny: Fastest, less accurate\\n"
            "• Base: Balanced (recommended)\\n"
            "• Small/Medium/Large: Higher accuracy, slower"
        )
        model_info.setWordWrap(True)
        whisper_layout.addWidget(model_info)
        whisper_group.setLayout(whisper_layout)
        engine_layout.addWidget(whisper_group)
        
        engine_layout.addStretch()
        tabs.addTab(engine_tab, "GPU & Models")
        
        # ===== CACHE TAB =====
        cache_tab = QWidget()
        cache_layout = QVBoxLayout(cache_tab)
        
        cache_group = QGroupBox("Translation Cache")
        cache_group_layout = QVBoxLayout()
        
        self.cache_enabled = QCheckBox("Enable Translation Caching")
        self.cache_enabled.setChecked(config.get("cache_translations", True))
        cache_group_layout.addWidget(self.cache_enabled)
        
        self.cache_expiry_spin = QSpinBox()
        self.cache_expiry_spin.setRange(1, 365)
        self.cache_expiry_spin.setValue(config.get("cache_expiry_days", 7))
        self.cache_expiry_spin.setSuffix(" days")
        cache_group_layout.addWidget(QLabel("Cache Expiry:"))
        cache_group_layout.addWidget(self.cache_expiry_spin)
        
        cache_group.setLayout(cache_group_layout)
        cache_layout.addWidget(cache_group)
        
        # Data locations
        data_group = QGroupBox("Data Locations")
        data_layout = QVBoxLayout()
        data_layout.addWidget(QLabel(f"Configuration: {CONFIG_FILE}"))
        data_layout.addWidget(QLabel(f"Database: {DB_FILE}"))
        data_layout.addWidget(QLabel(f"Audio Cache: {AUDIO_DIR}"))
        data_layout.addWidget(QLabel(f"Vosk Models: {VOSK_MODELS_DIR}"))
        data_group.setLayout(data_layout)
        cache_layout.addWidget(data_group)
        
        cache_layout.addStretch()
        tabs.addTab(cache_tab, "Cache & Data")
        
        layout.addWidget(tabs)
        
        # Professional action buttons with Material Design 3 styling
        buttons = QHBoxLayout()
        buttons.setSpacing(12)
        
        save_btn = QPushButton("✔ Save & Apply")
        save_btn.clicked.connect(self.save_settings)
        save_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #4CAF50, stop:1 #388E3C);
                color: white;
                font-weight: 600;
                padding: 12px 28px;
                font-size: 14px;
                border: none;
                border-radius: 10px;
                letter-spacing: 0.5px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #5FD068, stop:1 #4CAF50);
            }
            QPushButton:pressed {
                background: #2E7D32;
            }
        """)
        
        cancel_btn = QPushButton("✖ Cancel")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: rgba(60,60,70,0.8);
                color: #e8eaed;
                font-weight: 500;
                padding: 12px 28px;
                font-size: 14px;
                border: 1.5px solid rgba(255,255,255,0.1);
                border-radius: 10px;
            }
            QPushButton:hover {
                background: rgba(75,75,85,0.9);
                border: 1.5px solid rgba(255,255,255,0.2);
            }
        """)
        
        buttons.addStretch()
        buttons.addWidget(save_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)
    
    def choose_text_color(self):
        color = QColorDialog.getColor(QColor(self.text_color), self, "Choose Text Color")
        if color.isValid():
            self.text_color = color.name()
            self.text_color_btn.setStyleSheet(f"background-color: {self.text_color};")
    
    def save_settings(self):
        # Save all settings
        config.set("theme", self.theme_combo.currentText().lower())
        config.set("font_size", self.font_size_spin.value())
        config.set("text_color", self.text_color)
        config.set("animation_duration", self.anim_duration_spin.value())
        config.set("max_words", self.max_words_spin.value())
        config.set("subtitle_lines", self.subtitle_lines_spin.value())
        config.set("subtitle_update_delay", self.subtitle_delay_spin.value())
        config.set("tts_rate", self.tts_rate_spin.value())
        config.set("volume", self.volume_slider.value() / 100.0)
        config.set("audio_device_input", self.device_combo.currentData())
        config.set("use_gpu", self.use_gpu_check.isChecked())
        config.set("whisper_model", self.whisper_model_combo.currentData())
        config.set("cache_translations", self.cache_enabled.isChecked())
        config.set("cache_expiry_days", self.cache_expiry_spin.value())
        
        # Apply TTS volume immediately
        tts_manager.set_volume(self.volume_slider.value() / 100.0)
        
        # Apply GPU setting immediately
        whisper_manager.set_device(self.use_gpu_check.isChecked())
        
        self.accept()

