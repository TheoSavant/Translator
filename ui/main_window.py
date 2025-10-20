"""Main application window"""
import logging
import time
from datetime import datetime
from collections import deque
from pathlib import Path
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from deep_translator.constants import GOOGLE_LANGUAGES_TO_CODES
from langdetect import detect, LangDetectException, detect_langs
from config import config
from config.constants import RecognitionEngine, BASE_DIR
from database import db
from core import translator, tts_manager, ContinuousSpeechRecognitionThread
from core import conversation_mode, contextual_engine, offline_translator
from core import translation_mode_manager, TranslationMode, voice_duplication, platform_integration
from models import whisper_manager
from utils import audio_device_manager, gpu_manager
from .overlay import ResizableOverlay
from .settings_dialog import SettingsDialog
from .model_manager_dialog import ModelManagerDialog

log = logging.getLogger("Translator")

class LiveTranslatorApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🌍 Universal Live Translator — Professional Edition v4.5")
        self.resize(1100, 850)
        self.setMinimumSize(900, 650)
        self.recognition_thread = None
        self.source_type = "microphone"
        self.translation_mode = "Continuous"
        self.recognition_engine = RecognitionEngine.GOOGLE
        self.overlay = ResizableOverlay()
        self.overlay.show()
        
        # Performance monitoring
        self.last_history_refresh = time.time()
        self.history_refresh_throttle = 2.0  # seconds
        
        self.setup_ui()
        self.apply_theme(config.get("theme", "dark"))
        self.load_settings()
    
    def setup_menu_bar(self):
        """Create organized menu bar for better UX"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("📁 File")
        
        export_action = QAction("💾 Export History", self)
        export_action.setShortcut("Ctrl+E")
        export_action.triggered.connect(self.export_history)
        file_menu.addAction(export_action)
        
        clear_action = QAction("🗑️ Clear History", self)
        clear_action.triggered.connect(self.clear_history)
        file_menu.addAction(clear_action)
        
        file_menu.addSeparator()
        
        quit_action = QAction("❌ Quit", self)
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)
        
        # Tools menu
        tools_menu = menubar.addMenu("🛠️ Tools")
        
        models_action = QAction("📥 Model Manager", self)
        models_action.setShortcut("Ctrl+Shift+M")
        models_action.triggered.connect(self.show_models)
        tools_menu.addAction(models_action)
        
        voice_action = QAction("🎙️ Voice Models", self)
        voice_action.triggered.connect(self.show_rvc_models)
        tools_menu.addAction(voice_action)
        
        platforms_action = QAction("🔗 Platform Integrations", self)
        platforms_action.triggered.connect(self.show_platforms)
        tools_menu.addAction(platforms_action)
        
        # View menu
        view_menu = menubar.addMenu("👁️ View")
        
        theme_action = QAction("🌓 Toggle Theme", self)
        theme_action.setShortcut("Ctrl+D")
        theme_action.triggered.connect(self.toggle_theme)
        view_menu.addAction(theme_action)
        
        overlay_action = QAction("👁️ Toggle Overlay", self)
        overlay_action.setShortcut("Ctrl+O")
        overlay_action.triggered.connect(self.toggle_overlay)
        view_menu.addAction(overlay_action)
        
        # Settings menu
        settings_menu = menubar.addMenu("⚙️ Settings")
        
        settings_action = QAction("⚙️ Open Settings", self)
        settings_action.setShortcut("Ctrl+Shift+S")
        settings_action.triggered.connect(self.show_settings)
        settings_menu.addAction(settings_action)
        
        # Help menu
        help_menu = menubar.addMenu("❓ Help")
        
        help_action = QAction("📖 Show Help", self)
        help_action.setShortcut("F1")
        help_action.triggered.connect(self.show_help)
        help_menu.addAction(help_action)
    
    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(12, 12, 12, 12)
        
        # Create menu bar for better organization
        self.setup_menu_bar()
        
        # Compact status bar at the top
        status_bar = QHBoxLayout()
        status_bar.setSpacing(10)
        
        # Status with enhanced styling
        self.status_label = QLabel("🌐 Ready")
        self.status_label.setStyleSheet("""
            QLabel {
                font-size: 13px;
                font-weight: 500;
                color: #82c8ff;
                padding: 5px 10px;
                background: rgba(130,200,255,0.1);
                border-radius: 6px;
                border: 1px solid rgba(130,200,255,0.2);
            }
        """)
        status_bar.addWidget(self.status_label)
        
        # GPU status indicator
        gpu_color = "#4CAF50" if gpu_manager.is_gpu_available() else "#FFC107"
        gpu_bg = "rgba(76,175,80,0.15)" if gpu_manager.is_gpu_available() else "rgba(255,193,7,0.15)"
        self.gpu_status = QLabel(f"🚀 {gpu_manager.device_name}")
        self.gpu_status.setStyleSheet(f"""
            QLabel {{
                color: {gpu_color};
                font-weight: 600;
                font-size: 12px;
                padding: 5px 10px;
                background: {gpu_bg};
                border-radius: 6px;
                border: 1px solid {gpu_color};
            }}
        """)
        self.gpu_status.setToolTip(f"Device: {gpu_manager.device}\nCUDA: {gpu_manager.has_cuda}\nMPS: {gpu_manager.has_mps}")
        status_bar.addWidget(self.gpu_status)
        
        # Performance monitor
        self.perf_label = QLabel("⚡ Ready")
        self.perf_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                font-weight: 500;
                color: #9aa0a6;
                padding: 5px 10px;
                background: rgba(154,160,166,0.08);
                border-radius: 6px;
            }
        """)
        self.perf_label.setToolTip("Real-time processing metrics")
        status_bar.addWidget(self.perf_label)
        
        status_bar.addStretch()
        main_layout.addLayout(status_bar)
        
        # Simplified config section - organized in tabs
        config_tabs = QTabWidget()
        config_tabs.setMaximumHeight(220)
        
        # Tab 1: Basic Configuration
        basic_tab = QWidget()
        basic_layout = QVBoxLayout(basic_tab)
        basic_layout.setSpacing(8)
        basic_layout.setContentsMargins(10, 10, 10, 10)
        
        # Languages - more compact
        lang_row = QHBoxLayout()
        lang_row.setSpacing(8)
        lang_row.addWidget(QLabel("From:"))
        self.source_lang_combo = QComboBox()
        self.populate_languages(self.source_lang_combo, True)
        self.source_lang_combo.setToolTip("Source language (Auto for detection)")
        lang_row.addWidget(self.source_lang_combo, 2)
        
        self.swap_btn = QPushButton("⇄")
        self.swap_btn.setMaximumWidth(40)
        self.swap_btn.setMinimumHeight(30)
        self.swap_btn.clicked.connect(self.swap_languages)
        self.swap_btn.setToolTip("Swap languages")
        lang_row.addWidget(self.swap_btn)
        
        lang_row.addWidget(QLabel("To:"))
        self.target_lang_combo = QComboBox()
        self.populate_languages(self.target_lang_combo)
        self.target_lang_combo.setToolTip("Target language")
        lang_row.addWidget(self.target_lang_combo, 2)
        basic_layout.addLayout(lang_row)
        
        # Engine and Mode
        engine_row = QHBoxLayout()
        engine_row.setSpacing(8)
        engine_row.addWidget(QLabel("Engine:"))
        self.engine_combo = QComboBox()
        self.engine_combo.addItem("🌐 Google", RecognitionEngine.GOOGLE.value)
        self.engine_combo.addItem("💻 Vosk", RecognitionEngine.VOSK.value)
        self.engine_combo.addItem("🤖 Whisper", RecognitionEngine.WHISPER.value)
        self.engine_combo.currentIndexChanged.connect(self.on_engine_changed)
        engine_row.addWidget(self.engine_combo, 1)
        
        engine_row.addWidget(QLabel("Mode:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Standard", "Simultaneous", "Universal", "Voice Clone"])
        self.mode_combo.currentTextChanged.connect(self.on_translation_mode_changed)
        engine_row.addWidget(self.mode_combo, 1)
        basic_layout.addLayout(engine_row)
        
        basic_layout.addStretch()
        config_tabs.addTab(basic_tab, "🌐 Basic")
        
        # Tab 2: Advanced Settings
        adv_tab = QWidget()
        adv_layout = QVBoxLayout(adv_tab)
        adv_layout.setSpacing(8)
        adv_layout.setContentsMargins(10, 10, 10, 10)
        
        self.gpu_checkbox = QCheckBox("🚀 GPU Acceleration")
        self.gpu_checkbox.setChecked(config.get("use_gpu", True))
        self.gpu_checkbox.setEnabled(gpu_manager.is_gpu_available())
        self.gpu_checkbox.stateChanged.connect(self.on_gpu_toggled)
        adv_layout.addWidget(self.gpu_checkbox)
        
        self.conversation_mode_checkbox = QCheckBox("🗣️ Conversation Mode")
        self.conversation_mode_checkbox.setChecked(config.get("conversation_mode_enabled", False))
        self.conversation_mode_checkbox.stateChanged.connect(self.on_conversation_mode_toggled)
        self.conversation_mode_checkbox.setToolTip("Bidirectional auto-translation")
        adv_layout.addWidget(self.conversation_mode_checkbox)
        
        self.auto_mode_checkbox = QCheckBox("   ↳ Auto (Any Language)")
        self.auto_mode_checkbox.setChecked(config.get("conversation_auto_mode", False))
        self.auto_mode_checkbox.stateChanged.connect(self.on_auto_mode_toggled)
        adv_layout.addWidget(self.auto_mode_checkbox)
        
        self.slang_checkbox = QCheckBox("💬 Slang & Autocorrect")
        self.slang_checkbox.setChecked(config.get("slang_translation_enabled", True))
        self.slang_checkbox.stateChanged.connect(self.on_slang_toggled)
        adv_layout.addWidget(self.slang_checkbox)
        
        adv_layout.addStretch()
        config_tabs.addTab(adv_tab, "⚡ Advanced")
        
        main_layout.addWidget(config_tabs)
        
        # Input/Output
        io_splitter = QSplitter(Qt.Orientation.Vertical)
        
        input_widget = QWidget()
        input_layout = QVBoxLayout(input_widget)
        input_layout.setContentsMargins(0, 0, 0, 0)
        
        input_header = QHBoxLayout()
        input_header.addWidget(QLabel("🎙️ Input (Continuous)"))
        self.confidence_label = QLabel()
        input_header.addWidget(self.confidence_label)
        input_header.addStretch()
        self.word_count = QLabel("0 words")
        input_header.addWidget(self.word_count)
        input_layout.addLayout(input_header)
        
        self.input_text = QTextEdit()
        self.input_text.setPlaceholderText("🎤 Speak continuously - no need to stop...\n\nClick 'Start Continuous Listening' and speak naturally.\nYour words will appear here in real-time with timestamps and confidence scores.")
        self.input_text.textChanged.connect(self.update_word_count)
        self.input_text.setToolTip("Live transcription appears here with timestamps and confidence scores")
        input_layout.addWidget(self.input_text)
        
        io_splitter.addWidget(input_widget)
        
        output_widget = QWidget()
        output_layout = QVBoxLayout(output_widget)
        output_layout.setContentsMargins(0, 0, 0, 0)
        
        output_header = QHBoxLayout()
        output_header.addWidget(QLabel("🈯 Translation (Async Pipeline)"))
        output_header.addStretch()
        self.copy_btn = QPushButton("📋 Copy")
        self.copy_btn.clicked.connect(self.copy_output)
        output_header.addWidget(self.copy_btn)
        output_layout.addLayout(output_header)
        
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setPlaceholderText("🌐 Translation appears here instantly...\n\nTranslations are processed in real-time through async pipeline.\nResults include timestamps and confidence scores.")
        self.output_text.setToolTip("Translated text with confidence scores and timestamps")
        output_layout.addWidget(self.output_text)
        
        io_splitter.addWidget(output_widget)
        main_layout.addWidget(io_splitter, 3)
        
        # Cleaner, better organized controls
        controls = QWidget()
        controls_layout = QVBoxLayout(controls)
        controls_layout.setSpacing(10)
        
        # Primary control - bigger and prominent
        self.listen_btn = QPushButton("🎤 Start Listening")
        self.listen_btn.setMinimumHeight(50)
        self.listen_btn.clicked.connect(self.toggle_listening)
        self.listen_btn.setStyleSheet("""
            QPushButton {
                font-weight: 600;
                padding: 12px 20px;
                font-size: 15px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #4CAF50, stop:1 #388E3C);
                color: white;
                border: none;
                border-radius: 10px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #5FD068, stop:1 #4CAF50);
            }
        """)
        self.listen_btn.setToolTip("Start/stop continuous speech recognition (Ctrl+L)")
        controls_layout.addWidget(self.listen_btn)
        
        # Secondary controls - organized in rows
        row1 = QHBoxLayout()
        row1.setSpacing(8)
        
        self.translate_btn = QPushButton("🔄 Translate")
        self.translate_btn.clicked.connect(self.translate_manual)
        self.translate_btn.setToolTip("Manually translate (Ctrl+T)")
        row1.addWidget(self.translate_btn)
        
        self.speak_btn = QPushButton("🔊 Speak")
        self.speak_btn.clicked.connect(self.speak_output)
        self.speak_btn.setToolTip("Speak output (Ctrl+S)")
        row1.addWidget(self.speak_btn)
        
        self.stop_btn = QPushButton("🔇 Stop")
        self.stop_btn.clicked.connect(lambda: tts_manager.stop())
        self.stop_btn.setToolTip("Stop TTS playback")
        row1.addWidget(self.stop_btn)
        
        controls_layout.addLayout(row1)
        
        row2 = QHBoxLayout()
        row2.setSpacing(8)
        
        self.source_btn = QPushButton("🎧 System Audio")
        self.source_btn.clicked.connect(self.toggle_source)
        self.source_btn.setToolTip("Switch audio input source")
        row2.addWidget(self.source_btn)
        
        self.overlay_btn = QPushButton("👁️ Overlay")
        self.overlay_btn.clicked.connect(self.toggle_overlay)
        self.overlay_btn.setToolTip("Toggle overlay (Ctrl+O)")
        row2.addWidget(self.overlay_btn)
        
        controls_layout.addLayout(row2)
        
        # Options row
        options_row = QHBoxLayout()
        options_row.setSpacing(15)
        
        self.auto_speak = QCheckBox("🔊 Auto-speak")
        self.auto_speak.setChecked(config.get("auto_speak", True))
        self.auto_speak.stateChanged.connect(lambda: config.set("auto_speak", self.auto_speak.isChecked()))
        options_row.addWidget(self.auto_speak)
        
        self.show_conf = QCheckBox("🎯 Show confidence")
        self.show_conf.setChecked(config.get("show_confidence", True))
        self.show_conf.stateChanged.connect(lambda: config.set("show_confidence", self.show_conf.isChecked()))
        options_row.addWidget(self.show_conf)
        
        options_row.addStretch()
        
        # Word count indicator
        self.word_count = QLabel("0 words")
        self.word_count.setStyleSheet("color: #9aa0a6; font-size: 12px;")
        options_row.addWidget(self.word_count)
        
        controls_layout.addLayout(options_row)
        
        main_layout.addWidget(controls)
        
        # Compact history section
        history_group = QGroupBox("📜 History")
        history_layout = QVBoxLayout()
        history_layout.setSpacing(8)
        
        # Simplified search bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Search history... (Ctrl+F)")
        self.search_input.textChanged.connect(self.search_history)
        history_layout.addWidget(self.search_input)
        
        self.history_list = QListWidget()
        self.history_list.itemDoubleClicked.connect(self.load_history_item)
        history_layout.addWidget(self.history_list)
        
        history_group.setLayout(history_layout)
        main_layout.addWidget(history_group, 1)
        
        self.statusBar().showMessage("🚀 Ready - Professional Edition v4.5")
        self.refresh_history()
        self.setup_shortcuts()
    
    def setup_shortcuts(self):
        """Setup professional keyboard shortcuts for accessibility"""
        # Help and information
        QShortcut(QKeySequence("F1"), self, self.show_help)
        QShortcut(QKeySequence("Ctrl+H"), self, self.show_help)
        
        # Main controls
        QShortcut(QKeySequence("Ctrl+L"), self, self.toggle_listening)
        QShortcut(QKeySequence("Ctrl+T"), self, self.translate_manual)
        QShortcut(QKeySequence("Ctrl+S"), self, self.speak_output)
        QShortcut(QKeySequence("Ctrl+O"), self, self.toggle_overlay)
        QShortcut(QKeySequence("Ctrl+D"), self, self.toggle_theme)
        
        # Advanced shortcuts for power users
        QShortcut(QKeySequence("Ctrl+Shift+S"), self, self.show_settings)
        QShortcut(QKeySequence("Ctrl+Shift+M"), self, self.show_models)
        QShortcut(QKeySequence("Ctrl+E"), self, self.export_history)
        QShortcut(QKeySequence("Ctrl+F"), self, self.focus_search)
        QShortcut(QKeySequence("Ctrl+Shift+C"), self, self.clear_io_fields)
        
        # Application control
        QShortcut(QKeySequence("Ctrl+Q"), self, self.close)
        QShortcut(QKeySequence("Alt+F4"), self, self.close)
        
        log.info("✅ Keyboard shortcuts configured for accessibility")
    
    def focus_search(self):
        """Focus the search input for accessibility"""
        self.search_input.setFocus()
        self.search_input.selectAll()
    
    def clear_io_fields(self):
        """Clear input and output fields (Ctrl+Shift+C)"""
        self.input_text.clear()
        self.output_text.clear()
        self.overlay.clear_subtitles()
        self.statusBar().showMessage("✅ Cleared input/output fields", 2000)
    
    def show_help(self):
        help_text = f"""
🌍 Universal Live Translator — Professional Edition v3.5

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✨ CONTINUOUS LISTENING
• Microphone never stops - speak naturally without interruptions
• Async processing pipeline - zero blocking, maximum performance
• Parallel recognition and translation for instant results
• Real-time performance monitoring with queue status

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📺 NETFLIX/GOOGLE-STYLE OVERLAY
• Real-time word-by-word subtitle updates
• Professional glassmorphic design with blur effects
• Smooth fade and scroll animations
• Shows last {config.get("subtitle_lines", 3)} lines of text
• Auto-wrapping at sentence breaks

Resizing Controls:
  🔸 Drag corners → Resize diagonally
  🔸 Drag edges → Resize in one direction
  🔸 Drag center → Move window
  🔸 Minimum size enforced for readability

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🚀 GPU ACCELERATION
• Current Status: {gpu_manager.device_name}
• Device: {gpu_manager.device.upper()}
• CUDA: {'✅ Available' if gpu_manager.has_cuda else '❌ Not detected'}
• MPS: {'✅ Available' if gpu_manager.has_mps else '❌ Not detected'}
• Performance: 10-20x faster Whisper transcription
• Configure in Settings (⚙️) for instant switching

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚡ KEYBOARD SHORTCUTS
• F1 → Show this help
• Ctrl+L → Start/stop continuous listening
• Ctrl+T → Manual translate
• Ctrl+S → Speak output
• Ctrl+O → Toggle overlay
• Ctrl+D → Toggle dark/light theme
• Ctrl+Q → Quit application

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎨 PROFESSIONAL FEATURES
• Material Design 3 UI with smooth animations
• Netflix-level glassmorphic effects
• Professional color palette and typography
• Enhanced status indicators with real-time feedback
• Accessible design with keyboard navigation
• Smooth micro-interactions throughout

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📥 MODEL MANAGEMENT
• Click 'Models' to download Whisper/Vosk models
• Whisper: tiny, base, small, medium, large
• Vosk: Offline speech recognition for 4+ languages
• Auto-download on first use

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚙️ SETTINGS
All settings editable via Settings dialog:
• Appearance: Theme, fonts, colors, animations
• Audio: TTS rate, volume, input devices
• GPU & Models: Acceleration, Whisper model size
• Cache: Translation caching, expiry settings
• Overlay: Subtitle lines, update speed

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 PRO TIPS
• Use GPU acceleration for 10-20x faster transcription
• Set subtitle update delay to 5-10ms for instant captions
• Enable translation caching for faster repeated phrases
• Use 'base' Whisper model for best speed/accuracy balance
• Resize overlay to fit your screen perfectly

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Enjoy your professional-grade translator! 🚀
"""
        msg = QMessageBox(self)
        msg.setWindowTitle("✨ Help — Universal Live Translator v3.5")
        msg.setText(help_text)
        msg.setIcon(QMessageBox.Icon.Information)
        # Set minimum width for better formatting
        msg.setStyleSheet("QLabel{min-width: 650px; font-family: monospace;}")
        msg.exec()
    
    def populate_languages(self, combo, include_auto=False):
        if include_auto:
            combo.addItem("🔍 Auto", "auto")
        langs = sorted([(n.title(), c) for n, c in GOOGLE_LANGUAGES_TO_CODES.items()], key=lambda x: x[0])
        for name, code in langs:
            combo.addItem(name, code)
    
    def load_settings(self):
        src = config.get("source_language", "auto")
        tgt = config.get("target_language", "fr")
        engine = config.get("recognition_engine", "google")
        idx = self.source_lang_combo.findData(src)
        if idx >= 0:
            self.source_lang_combo.setCurrentIndex(idx)
        idx = self.target_lang_combo.findData(tgt)
        if idx >= 0:
            self.target_lang_combo.setCurrentIndex(idx)
        idx = self.engine_combo.findData(engine)
        if idx >= 0:
            self.engine_combo.setCurrentIndex(idx)
        
        # Initialize conversation mode
        conv_enabled = config.get("conversation_mode_enabled", False)
        auto_mode = config.get("conversation_auto_mode", False)
        if conv_enabled:
            src_lang = src if src != "auto" else "en"
            conversation_mode.enable(src_lang, tgt, auto_mode)
        
        # Initialize translator contextual features
        slang_enabled = config.get("slang_translation_enabled", True)
        translator.use_slang_expansion = slang_enabled
        translator.use_autocorrect = slang_enabled
    
    def on_engine_changed(self):
        engine_val = self.engine_combo.currentData()
        self.recognition_engine = RecognitionEngine(engine_val)
        config.set("recognition_engine", engine_val)
        if self.recognition_thread and self.recognition_thread.isRunning():
            self.stop_listening()
            QTimer.singleShot(500, self.start_listening)
    
    def on_gpu_toggled(self):
        """Handle GPU acceleration toggle with professional feedback"""
        use_gpu = self.gpu_checkbox.isChecked()
        config.set("use_gpu", use_gpu)
        whisper_manager.set_device(use_gpu)
        device = whisper_manager.device
        
        # Update GPU status indicator with color coding
        gpu_color = "#4CAF50" if use_gpu and gpu_manager.is_gpu_available() else "#FFC107"
        gpu_bg = "rgba(76,175,80,0.15)" if use_gpu and gpu_manager.is_gpu_available() else "rgba(255,193,7,0.15)"
        self.gpu_status.setText(f"🚀 {device.upper()}")
        self.gpu_status.setStyleSheet(f"""
            QLabel {{
                color: {gpu_color};
                font-weight: 600;
                font-size: 13px;
                padding: 6px 12px;
                background: {gpu_bg};
                border-radius: 8px;
                border: 1px solid {gpu_color};
            }}
        """)
        
        # Show professional status message
        if use_gpu and gpu_manager.is_gpu_available():
            self.statusBar().showMessage(f"✅ GPU acceleration ENABLED - Using {device.upper()} (10-20x faster!)", 4000)
        else:
            self.statusBar().showMessage(f"⚠️ GPU acceleration disabled - Using {device.upper()}", 4000)
    
    def on_conversation_mode_toggled(self):
        """Handle conversation mode toggle"""
        enabled = self.conversation_mode_checkbox.isChecked()
        config.set("conversation_mode_enabled", enabled)
        
        if enabled:
            # Get current language settings
            src_lang = self.source_lang_combo.currentData()
            tgt_lang = self.target_lang_combo.currentData()
            
            # Use 'en' as default if auto is selected
            if src_lang == "auto":
                src_lang = "en"
            
            # Enable conversation mode
            auto_mode = self.auto_mode_checkbox.isChecked()
            conversation_mode.enable(src_lang, tgt_lang, auto_mode)
            
            self.statusBar().showMessage(
                f"🗣️ Conversation Mode ENABLED: {src_lang} ↔ {tgt_lang} "
                f"({'Auto' if auto_mode else 'Bidirectional'})", 4000
            )
        else:
            conversation_mode.disable()
            self.statusBar().showMessage("Conversation Mode disabled", 3000)
    
    def on_auto_mode_toggled(self):
        """Handle auto mode toggle for conversation mode"""
        auto_mode = self.auto_mode_checkbox.isChecked()
        config.set("conversation_auto_mode", auto_mode)
        
        if conversation_mode.enabled:
            conversation_mode.auto_mode = auto_mode
            mode_text = "Auto (Any Language)" if auto_mode else "Bidirectional"
            self.statusBar().showMessage(f"Conversation Mode: {mode_text}", 3000)
    
    def on_slang_toggled(self):
        """Handle slang translation and autocorrect toggle"""
        enabled = self.slang_checkbox.isChecked()
        config.set("slang_translation_enabled", enabled)
        
        # Update translator settings
        translator.use_slang_expansion = enabled
        translator.use_autocorrect = enabled
        
        if enabled:
            self.statusBar().showMessage("💬 Slang translation & autocorrect ENABLED", 3000)
        else:
            self.statusBar().showMessage("Slang translation & autocorrect disabled", 3000)
    
    def show_models(self):
        dialog = ModelManagerDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Refresh UI if needed
            pass
    
    def show_platforms(self):
        """Show platform integrations dialog"""
        from .platform_integrations_dialog import PlatformIntegrationsDialog
        dialog = PlatformIntegrationsDialog(self)
        dialog.exec()
    
    def show_settings(self):
        dialog = SettingsDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Apply theme change if needed
            theme = config.get("theme", "dark")
            self.apply_theme(theme)
            # Update overlay style and configuration
            self.overlay.apply_style()
            # Update subtitle delay setting
            self.overlay.subtitle_update_delay = config.get("subtitle_update_delay", 10) / 1000.0
            # Recreate displayed_lines deque with new max lines
            max_lines = config.get("subtitle_lines", 3)
            old_lines = list(self.overlay.displayed_lines)
            self.overlay.displayed_lines = deque(old_lines, maxlen=max_lines)
            # Update GPU status
            device = whisper_manager.device
            self.gpu_status.setText(f"🚀 Device: {device.upper()}")
            self.gpu_checkbox.setChecked(config.get("use_gpu", True))
            self.statusBar().showMessage("Settings saved - Subtitle speed updated", 3000)
    
    def show_rvc_models(self):
        """Show RVC voice duplication models dialog"""
        from .rvc_model_dialog import RVCModelDialog
        dialog = RVCModelDialog(self)
        dialog.exec()
    
    def on_translation_mode_changed(self, mode_text: str):
        """Handle translation mode change"""
        mode_map = {
            "Standard": TranslationMode.STANDARD,
            "Simultaneous": TranslationMode.SIMULTANEOUS,
            "Universal": TranslationMode.UNIVERSAL,
            "Voice Clone": TranslationMode.VOICE_DUPLICATION
        }
        
        selected_mode = mode_map.get(mode_text, TranslationMode.STANDARD)
        translation_mode_manager.set_mode(selected_mode)
        
        # Enable voice duplication if that mode is selected
        if selected_mode == TranslationMode.VOICE_DUPLICATION:
            if voice_duplication.get_current_model():
                voice_duplication.enable()
            else:
                QMessageBox.information(
                    self,
                    "Voice Clone Mode",
                    "No voice model selected. Please add and activate a voice model in Voice Models manager."
                )
        
        self.translation_mode = mode_text
        log.info(f"Translation mode changed to: {mode_text}")
    
    def swap_languages(self):
        """Swap source and target languages with validation"""
        if self.source_lang_combo.currentData() == "auto":
            self.statusBar().showMessage("⚠️ Cannot swap with auto-detect enabled", 3000)
            return
        
        src_idx = self.source_lang_combo.currentIndex()
        tgt_idx = self.target_lang_combo.currentIndex()
        
        # Swap the selections
        self.source_lang_combo.setCurrentIndex(tgt_idx + 1)
        self.target_lang_combo.setCurrentIndex(src_idx - 1)
        
        # Show confirmation
        src_lang = self.source_lang_combo.currentText()
        tgt_lang = self.target_lang_combo.currentText()
        self.statusBar().showMessage(f"⇄ Languages swapped: {src_lang} → {tgt_lang}", 2000)
    
    def update_word_count(self):
        text = self.input_text.toPlainText()
        words = len(text.split()) if text.strip() else 0
        self.word_count.setText(f"{words} words")
    
    def toggle_listening(self):
        if self.recognition_thread and self.recognition_thread.isRunning():
            self.stop_listening()
        else:
            self.start_listening()
    
    def start_listening(self):
        if self.recognition_thread:
            self.recognition_thread.stop()
            self.recognition_thread.wait()
        
        src_lang = self.source_lang_combo.currentData()
        if src_lang == "auto":
            src_lang = "en"
        
        device_idx = config.get("audio_device_input", "default")
        if device_idx == "default":
            device_idx = None
        else:
            device_idx = int(device_idx)
        
        # Use continuous recognition thread
        self.recognition_thread = ContinuousSpeechRecognitionThread(
            self.source_type, src_lang, self.recognition_engine, device_idx
        )
        self.recognition_thread.phrase_detected.connect(self.handle_phrase, Qt.ConnectionType.QueuedConnection)
        self.recognition_thread.status_changed.connect(self.update_status_safe, Qt.ConnectionType.QueuedConnection)
        self.recognition_thread.error_occurred.connect(
            self.handle_recognition_error, Qt.ConnectionType.QueuedConnection
        )
        self.recognition_thread.performance_update.connect(self.update_performance, Qt.ConnectionType.QueuedConnection)
        self.recognition_thread.start()
        
        self.listen_btn.setText("⏹️ Stop Continuous Listening")
        self.listen_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #F44336, stop:1 #D32F2F);
                color: white;
                font-weight: 600;
                padding: 14px 24px;
                font-size: 15px;
                border: none;
                border-radius: 12px;
                letter-spacing: 0.5px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #FF5252, stop:1 #F44336);
            }
            QPushButton:pressed {
                background: #B71C1C;
            }
        """)
        self.statusBar().showMessage(f"🎙️ Continuous listening active ({self.recognition_engine.value} engine) - Speak naturally!")
    
    def stop_listening(self):
        if self.recognition_thread:
            self.recognition_thread.stop()
            self.recognition_thread.wait()
            self.recognition_thread = None
        self.listen_btn.setText("🎤 Start Continuous Listening")
        self.listen_btn.setStyleSheet("""
            QPushButton {
                font-weight: 600;
                padding: 14px 24px;
                font-size: 15px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #4CAF50, stop:1 #388E3C);
                color: white;
                border: none;
                border-radius: 12px;
                letter-spacing: 0.5px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #5FD068, stop:1 #4CAF50);
            }
        """)
        self.statusBar().showMessage("Stopped")
        self.perf_label.setText("⚡ Performance: Idle")
    
    def toggle_source(self):
        """Toggle audio source with professional feedback"""
        self.source_type = "system" if self.source_type == "microphone" else "microphone"
        self.source_btn.setText("🎤 Microphone" if self.source_type == "system" else "🎧 System Audio")
        
        # Show status update
        source_name = "🎤 Microphone" if self.source_type == "microphone" else "🎧 System Audio"
        self.statusBar().showMessage(f"⇄ Switched to {source_name}", 2000)
        
        # Restart listening if active
        if self.recognition_thread and self.recognition_thread.isRunning():
            self.statusBar().showMessage(f"↻ Restarting with {source_name}...", 2000)
            self.stop_listening()
            QTimer.singleShot(500, self.start_listening)
    
    def update_status_safe(self, message):
        """Thread-safe status update"""
        QMetaObject.invokeMethod(
            self.statusBar(), "showMessage",
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(str, message)
        )
    
    def handle_recognition_error(self, error_msg):
        """Thread-safe error handling"""
        QMessageBox.warning(self, "Error", error_msg)
        self.stop_listening()
    
    def update_performance(self, perf_data):
        """Update professional performance indicators (called from signal, already thread-safe)"""
        avg_time = perf_data.get('avg_processing_time', 0)
        rec_queue = perf_data.get('recognition_queue', 0)
        trans_queue = perf_data.get('translation_queue', 0)
        device = perf_data.get('device', 'N/A')
        
        # Color-coded performance indicator
        if avg_time < 300:
            color = "#4CAF50"  # Green - Excellent
            status = "Excellent"
        elif avg_time < 800:
            color = "#FFC107"  # Yellow - Good
            status = "Good"
        else:
            color = "#FF5722"  # Red - Slow
            status = "Slow"
        
        self.perf_label.setText(
            f"⚡ {avg_time:.0f}ms ({status}) | Queue: {rec_queue}/{trans_queue} | {device.upper()}"
        )
        self.perf_label.setStyleSheet(f"""
            QLabel {{
                font-size: 13px;
                font-weight: 500;
                color: {color};
                padding: 6px 12px;
                background: rgba({int(color[1:3], 16)},{int(color[3:5], 16)},{int(color[5:7], 16)},0.12);
                border-radius: 8px;
                border: 1px solid {color};
            }}
        """)
    
    def handle_phrase(self, phrase, confidence):
        if not phrase.strip():
            return
        
        cursor = self.input_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        timestamp = datetime.now().strftime("%H:%M:%S")
        conf_str = f" [{confidence:.0%}]" if config.get("show_confidence") else ""
        cursor.insertText(f"[{timestamp}]{conf_str} {phrase}\n")
        self.input_text.setTextCursor(cursor)
        self.input_text.ensureCursorVisible()
        self.confidence_label.setText(f"Confidence: {confidence:.0%}")
        
        if self.translation_mode in ["Real-time", "Continuous"]:
            # Async translation - non-blocking
            self.translate_phrase_async(phrase, confidence)
    
    def translate_phrase_async(self, phrase, speech_conf=1.0):
        """Async translation - doesn't block recognition, with conversation mode support"""
        src_lang = self.source_lang_combo.currentData()
        tgt_lang = self.target_lang_combo.currentData()
        
        # Auto-detect if needed
        if src_lang == "auto":
            try:
                detections = detect_langs(phrase)
                src_lang = detections[0].lang if detections else "en"
            except:
                src_lang = "en"
        
        # Conversation mode will override src/tgt in the translator if enabled
        # So we just pass the current settings and let conversation_mode handle it
        
        def on_translation_complete(result):
            translated, duration, trans_conf = result
            combined_conf = speech_conf * trans_conf
            timestamp = datetime.now().strftime("%H:%M:%S")
            conf_str = f" [{combined_conf:.0%}]" if config.get("show_confidence") else ""
            
            self.output_text.append(f"[{timestamp}]{conf_str} {translated}")
            self.overlay.add_text(translated)
            
            if config.get("auto_speak", True):
                tts_manager.speak(translated, tgt_lang)
            
            db.add_translation(phrase, translated, src_lang, tgt_lang, 
                             self.translation_mode, self.recognition_engine.value, 
                             combined_conf, duration)
            
            # Throttled history refresh
            self.refresh_history_throttled()
            
            self.statusBar().showMessage(f"✓ Translated ({duration}ms, {combined_conf:.0%})", 2000)
        
        # Submit async translation
        translator.translate_async(phrase, src_lang, tgt_lang, on_translation_complete)
    
    def translate_phrase(self, phrase, speech_conf=1.0):
        """Synchronous translation (for compatibility)"""
        src_lang = self.source_lang_combo.currentData()
        tgt_lang = self.target_lang_combo.currentData()
        
        if src_lang == "auto":
            try:
                detections = detect_langs(phrase)
                src_lang = detections[0].lang if detections else "en"
            except:
                src_lang = "en"
        
        translated, duration, trans_conf = translator.translate(phrase, src_lang, tgt_lang)
        combined_conf = speech_conf * trans_conf
        timestamp = datetime.now().strftime("%H:%M:%S")
        conf_str = f" [{combined_conf:.0%}]" if config.get("show_confidence") else ""
        
        self.output_text.append(f"[{timestamp}]{conf_str} {translated}")
        self.overlay.add_text(translated)
        
        if config.get("auto_speak", True):
            tts_manager.speak(translated, tgt_lang)
        
        db.add_translation(phrase, translated, src_lang, tgt_lang, 
                         self.translation_mode, self.recognition_engine.value, 
                         combined_conf, duration)
        
        self.refresh_history_throttled()
        self.statusBar().showMessage(f"Translated ({duration}ms, {combined_conf:.0%})", 2000)
    
    def translate_manual(self):
        text = self.input_text.toPlainText().strip()
        if not text:
            self.statusBar().showMessage("No text", 3000)
            return
        
        src_lang = self.source_lang_combo.currentData()
        tgt_lang = self.target_lang_combo.currentData()
        
        if src_lang == "auto":
            try:
                src_lang = detect_langs(text)[0].lang if detect_langs(text) else "en"
            except:
                src_lang = "en"
        
        self.statusBar().showMessage("Translating...")
        QApplication.processEvents()
        
        translated, duration, conf = translator.translate(text, src_lang, tgt_lang)
        self.output_text.clear()
        conf_str = f" [{conf:.0%}]" if config.get("show_confidence") else ""
        self.output_text.append(f"{translated}{conf_str}")
        self.overlay.add_text(translated)
        
        if config.get("auto_speak", True):
            tts_manager.speak(translated, tgt_lang)
        
        db.add_translation(text, translated, src_lang, tgt_lang, "Manual", "manual", conf, duration)
        self.refresh_history()
        self.statusBar().showMessage(f"Done ({duration}ms, {conf:.0%})", 3000)
    
    def speak_output(self):
        text = self.output_text.toPlainText().strip()
        if not text:
            return
        import re
        text = re.sub(r'\[.*?\]\s*', '', text)
        lang = self.target_lang_combo.currentData()
        tts_manager.speak(text, lang)
    
    def copy_output(self):
        """Copy output text to clipboard with professional feedback"""
        text = self.output_text.toPlainText()
        if not text.strip():
            self.statusBar().showMessage("⚠️ No text to copy", 2000)
            return
        
        import re
        # Remove timestamps and confidence scores
        text = re.sub(r'\[.*?\]\s*', '', text)
        QApplication.clipboard().setText(text)
        
        # Show success message with character count
        char_count = len(text)
        word_count = len(text.split())
        self.statusBar().showMessage(f"✅ Copied to clipboard! ({word_count} words, {char_count} characters)", 3000)
    
    def toggle_overlay(self):
        """Toggle overlay visibility with status feedback"""
        is_visible = not self.overlay.isVisible()
        self.overlay.setVisible(is_visible)
        config.set("overlay_visible", is_visible)
        
        status = "👁️ Overlay shown" if is_visible else "🚫 Overlay hidden"
        self.statusBar().showMessage(status, 2000)
    
    def refresh_history_throttled(self):
        """Throttled history refresh to avoid UI lag"""
        now = time.time()
        if now - self.last_history_refresh > self.history_refresh_throttle:
            self.refresh_history()
            self.last_history_refresh = now
    
    def refresh_history(self, search=""):
        self.history_list.clear()
        for row in db.get_history(50, search):
            try:
                dt = datetime.fromisoformat(row['timestamp'])
                time_str = dt.strftime("%H:%M")
            except:
                time_str = ""
            
            src_prev = row['source_text'][:40] + "..." if len(row['source_text']) > 40 else row['source_text']
            trans_prev = row['translated_text'][:40] + "..." if len(row['translated_text']) > 40 else row['translated_text']
            conf = row.get('confidence', 1.0)
            conf_str = f" [{conf:.0%}]" if conf < 1.0 else ""
            item_text = f"[{time_str}]{conf_str} {row['source_lang']}→{row['target_lang']} | {src_prev} ➜ {trans_prev}"
            
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, row)
            
            if conf >= 0.9:
                item.setForeground(QColor("#4CAF50"))
            elif conf >= 0.7:
                item.setForeground(QColor("#FFC107"))
            else:
                item.setForeground(QColor("#FF5722"))
            
            self.history_list.addItem(item)
    
    def search_history(self):
        self.refresh_history(self.search_input.text())
    
    def load_history_item(self, item):
        data = item.data(Qt.ItemDataRole.UserRole)
        if data:
            self.input_text.setPlainText(data['source_text'])
            self.output_text.setPlainText(data['translated_text'])
    
    def export_history(self):
        """Export history with professional feedback and error handling"""
        default_filename = f"translator_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        filename, _ = QFileDialog.getSaveFileName(
            self, 
            "💾 Export Translation History", 
            str(BASE_DIR / default_filename), 
            "Text Files (*.txt);;All Files (*)"
        )
        if filename:
            try:
                db.export_history(filename)
                # Count exported items
                with open(filename, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    count = len([l for l in lines if l.startswith('[')])
                
                QMessageBox.information(
                    self, 
                    "✅ Export Successful",
                    f"Successfully exported {count} translations to:\n\n{filename}"
                )
                self.statusBar().showMessage(f"✅ Exported {count} translations", 3000)
            except Exception as e:
                log.error(f"Export failed: {e}")
                QMessageBox.critical(
                    self, 
                    "❌ Export Failed",
                    f"Failed to export translation history:\n\n{str(e)}"
                )
    
    def clear_history(self):
        """Clear history with professional confirmation dialog"""
        reply = QMessageBox.question(
            self, 
            "🗑️ Clear History",
            "Are you sure you want to clear all translation history?\n\nThis action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            db.clear_history()
            self.refresh_history()
            self.statusBar().showMessage("✅ Translation history cleared", 3000)
    
    def toggle_theme(self):
        """Toggle theme with smooth transition feedback"""
        current = config.get("theme", "dark")
        new = "light" if current == "dark" else "dark"
        config.set("theme", new)
        self.apply_theme(new)
        
        # Professional feedback
        theme_name = "🌙 Dark Mode" if new == "dark" else "☀️ Light Mode"
        self.statusBar().showMessage(f"✅ Switched to {theme_name}", 2000)
        self.theme_btn.setText("☀️ Light" if new == "dark" else "🌙 Dark")
    
    def apply_theme(self, theme):
        if theme == "dark":
            # Netflix/Google-level Material Design 3 dark theme
            self.setStyleSheet("""
                QMainWindow, QWidget {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #0f0f14, stop:1 #1a1a20);
                    color: #e8eaed;
                    font-family: "Segoe UI", "SF Pro Display", -apple-system, system-ui, sans-serif;
                }
                QGroupBox {
                    border: 1.5px solid rgba(255,255,255,0.08);
                    border-radius: 16px;
                    margin-top: 14px;
                    padding-top: 22px;
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 rgba(42,42,50,0.4), stop:1 rgba(32,32,38,0.4));
                    font-size: 13px;
                }
                QGroupBox::title {
                    left: 18px;
                    padding: 0 12px;
                    color: #82c8ff;
                    font-weight: 600;
                    font-size: 14px;
                    letter-spacing: 0.5px;
                }
                QTextEdit, QListWidget, QLineEdit {
                    background: rgba(28,28,35,0.7);
                    border: 1.5px solid rgba(255,255,255,0.06);
                    border-radius: 12px;
                    padding: 12px;
                    selection-background-color: #82c8ff;
                    selection-color: #0f0f14;
                    font-size: 14px;
                    line-height: 1.6;
                }
                QTextEdit:focus, QLineEdit:focus {
                    border: 1.5px solid #82c8ff;
                    background: rgba(28,28,35,0.85);
                }
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 rgba(60,60,70,0.8), stop:1 rgba(45,45,55,0.8));
                    border: 1.5px solid rgba(255,255,255,0.1);
                    border-radius: 10px;
                    padding: 11px 20px;
                    font-weight: 500;
                    font-size: 13px;
                    color: #e8eaed;
                    letter-spacing: 0.3px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 rgba(75,75,85,0.9), stop:1 rgba(60,60,70,0.9));
                    border: 1.5px solid #82c8ff;
                    transform: translateY(-1px);
                }
                QPushButton:pressed {
                    background: rgba(45,45,55,0.95);
                    border: 1.5px solid #5fa8d3;
                    transform: translateY(0px);
                }
                QComboBox {
                    background: rgba(28,28,35,0.7);
                    border: 1.5px solid rgba(255,255,255,0.06);
                    border-radius: 10px;
                    padding: 9px 12px;
                    font-size: 13px;
                    min-height: 20px;
                }
                QComboBox:hover {
                    border: 1.5px solid #82c8ff;
                    background: rgba(28,28,35,0.85);
                }
                QComboBox::drop-down {
                    border: none;
                    width: 30px;
                }
                QComboBox::down-arrow {
                    image: none;
                    border-left: 5px solid transparent;
                    border-right: 5px solid transparent;
                    border-top: 6px solid #82c8ff;
                    margin-right: 8px;
                }
                QCheckBox {
                    spacing: 10px;
                    font-size: 13px;
                }
                QCheckBox::indicator {
                    width: 20px;
                    height: 20px;
                    border-radius: 6px;
                    border: 2px solid rgba(255,255,255,0.15);
                    background: rgba(28,28,35,0.7);
                }
                QCheckBox::indicator:hover {
                    border: 2px solid #82c8ff;
                    background: rgba(28,28,35,0.85);
                }
                QCheckBox::indicator:checked {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #82c8ff, stop:1 #5fa8d3);
                    border-color: #82c8ff;
                    image: none;
                }
                QStatusBar {
                    background: rgba(20,20,26,0.95);
                    border-top: 1.5px solid rgba(255,255,255,0.05);
                    color: #b8bbbe;
                    font-size: 12px;
                    padding: 5px;
                }
                QLabel {
                    color: #e8eaed;
                    font-size: 13px;
                }
                QScrollBar:vertical {
                    background: transparent;
                    width: 12px;
                    margin: 0;
                }
                QScrollBar::handle:vertical {
                    background: rgba(130,200,255,0.3);
                    border-radius: 6px;
                    min-height: 30px;
                }
                QScrollBar::handle:vertical:hover {
                    background: rgba(130,200,255,0.5);
                }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                    height: 0px;
                }
            """)
        else:
            # Netflix/Google-level Material Design 3 light theme
            self.setStyleSheet("""
                QMainWindow, QWidget {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #fafafa, stop:1 #f0f0f5);
                    color: #1f1f1f;
                    font-family: "Segoe UI", "SF Pro Display", -apple-system, system-ui, sans-serif;
                }
                QGroupBox {
                    border: 1.5px solid rgba(0,0,0,0.06);
                    border-radius: 16px;
                    margin-top: 14px;
                    padding-top: 22px;
                    background: rgba(255,255,255,0.85);
                    font-size: 13px;
                }
                QGroupBox::title {
                    left: 18px;
                    padding: 0 12px;
                    color: #1967d2;
                    font-weight: 600;
                    font-size: 14px;
                    letter-spacing: 0.5px;
                }
                QTextEdit, QListWidget, QLineEdit {
                    background: rgba(255,255,255,0.9);
                    border: 1.5px solid rgba(0,0,0,0.08);
                    border-radius: 12px;
                    padding: 12px;
                    selection-background-color: #1967d2;
                    selection-color: white;
                    font-size: 14px;
                    line-height: 1.6;
                }
                QTextEdit:focus, QLineEdit:focus {
                    border: 1.5px solid #1967d2;
                    background: white;
                }
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 rgba(255,255,255,0.95), stop:1 rgba(245,245,250,0.95));
                    border: 1.5px solid rgba(0,0,0,0.1);
                    border-radius: 10px;
                    padding: 11px 20px;
                    font-weight: 500;
                    font-size: 13px;
                    color: #1f1f1f;
                    letter-spacing: 0.3px;
                }
                QPushButton:hover {
                    background: white;
                    border: 1.5px solid #1967d2;
                    color: #1967d2;
                }
                QPushButton:pressed {
                    background: rgba(245,245,250,1);
                    border: 1.5px solid #1557b0;
                }
                QComboBox {
                    background: rgba(255,255,255,0.9);
                    border: 1.5px solid rgba(0,0,0,0.08);
                    border-radius: 10px;
                    padding: 9px 12px;
                    font-size: 13px;
                }
                QComboBox:hover {
                    border: 1.5px solid #1967d2;
                    background: white;
                }
                QCheckBox::indicator {
                    width: 20px;
                    height: 20px;
                    border-radius: 6px;
                    border: 2px solid rgba(0,0,0,0.2);
                    background: white;
                }
                QCheckBox::indicator:checked {
                    background: #1967d2;
                    border-color: #1967d2;
                }
                QStatusBar {
                    background: rgba(245,245,250,0.95);
                    border-top: 1.5px solid rgba(0,0,0,0.05);
                    color: #5f6368;
                    font-size: 12px;
                }
            """)
        
        # Update overlay style
        self.overlay.apply_style()
    
    def closeEvent(self, event):
        config.set("source_language", self.source_lang_combo.currentData())
        config.set("target_language", self.target_lang_combo.currentData())
        
        if self.recognition_thread:
            self.recognition_thread.stop()
            self.recognition_thread.wait()
        
        tts_manager.shutdown()
        audio_device_manager.cleanup()
        self.overlay.close()
        event.accept()

