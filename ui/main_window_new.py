"""Clean, organized main window with proper error handling and user-friendly UI"""
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
        self.resize(1200, 900)
        self.setMinimumSize(1000, 700)
        
        # Initialize state variables
        self.recognition_thread = None
        self.source_type = "microphone"
        self.translation_mode = "Continuous"
        self.recognition_engine = RecognitionEngine.GOOGLE
        self.is_listening = False
        
        # Initialize overlay
        self.overlay = ResizableOverlay()
        self.overlay.show()
        
        # Performance monitoring
        self.last_history_refresh = time.time()
        self.history_refresh_throttle = 2.0
        
        # Setup UI with proper error handling
        try:
            self.setup_ui()
            self.apply_theme(config.get("theme", "dark"))
            self.load_settings()
            self.setup_shortcuts()
            log.info("✅ UI setup completed successfully")
        except Exception as e:
            log.error(f"❌ UI setup failed: {e}")
            self.show_error_dialog("UI Setup Error", f"Failed to initialize the user interface:\n{str(e)}")
    
    def setup_ui(self):
        """Create a clean, organized UI with proper tabs and layout"""
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        # Create menu bar
        self.setup_menu_bar()
        
        # Status bar at the top
        self.setup_status_bar(main_layout)
        
        # Main content area with tabs
        self.setup_main_tabs(main_layout)
        
        # Control panel at the bottom
        self.setup_control_panel(main_layout)
        
        # Initialize status
        self.statusBar().showMessage("🚀 Ready - Professional Edition v4.5")
        self.refresh_history()
    
    def setup_status_bar(self, parent_layout):
        """Create a clean status bar with system information"""
        status_widget = QWidget()
        status_layout = QHBoxLayout(status_widget)
        status_layout.setSpacing(15)
        
        # Status indicator
        self.status_label = QLabel("🌐 Ready")
        self.status_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: 600;
                color: #4CAF50;
                padding: 8px 15px;
                background: rgba(76,175,80,0.1);
                border-radius: 8px;
                border: 2px solid rgba(76,175,80,0.3);
            }
        """)
        status_layout.addWidget(self.status_label)
        
        # GPU status
        gpu_color = "#4CAF50" if gpu_manager.is_gpu_available() else "#FFC107"
        self.gpu_status = QLabel(f"🚀 {gpu_manager.device_name}")
        self.gpu_status.setStyleSheet(f"""
            QLabel {{
                color: {gpu_color};
                font-weight: 600;
                font-size: 13px;
                padding: 8px 15px;
                background: rgba({int(gpu_color[1:3], 16)},{int(gpu_color[3:5], 16)},{int(gpu_color[5:7], 16)},0.1);
                border-radius: 8px;
                border: 2px solid {gpu_color};
            }}
        """)
        status_layout.addWidget(self.gpu_status)
        
        # Performance indicator
        self.perf_label = QLabel("⚡ Performance: Idle")
        self.perf_label.setStyleSheet("""
            QLabel {
                font-size: 13px;
                font-weight: 500;
                color: #9aa0a6;
                padding: 8px 15px;
                background: rgba(154,160,166,0.08);
                border-radius: 8px;
            }
        """)
        status_layout.addWidget(self.perf_label)
        
        status_layout.addStretch()
        parent_layout.addWidget(status_widget)
    
    def setup_main_tabs(self, parent_layout):
        """Create organized tabs for different functions"""
        self.main_tabs = QTabWidget()
        self.main_tabs.setTabPosition(QTabWidget.TabPosition.North)
        self.main_tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 2px solid rgba(255,255,255,0.1);
                border-radius: 12px;
                background: rgba(255,255,255,0.02);
            }
            QTabBar::tab {
                background: rgba(255,255,255,0.05);
                border: 1px solid rgba(255,255,255,0.1);
                padding: 12px 20px;
                margin-right: 2px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-weight: 600;
                font-size: 14px;
            }
            QTabBar::tab:selected {
                background: rgba(130,200,255,0.2);
                border-color: #82c8ff;
                color: #82c8ff;
            }
            QTabBar::tab:hover {
                background: rgba(255,255,255,0.1);
            }
        """)
        
        # Tab 1: Translation
        self.setup_translation_tab()
        
        # Tab 2: Settings
        self.setup_settings_tab()
        
        # Tab 3: History
        self.setup_history_tab()
        
        # Tab 4: Models
        self.setup_models_tab()
        
        parent_layout.addWidget(self.main_tabs, 1)
    
    def setup_translation_tab(self):
        """Translation tab with clean input/output areas"""
        translation_widget = QWidget()
        layout = QVBoxLayout(translation_widget)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Language selection
        lang_group = QGroupBox("🌍 Language Settings")
        lang_layout = QVBoxLayout(lang_group)
        lang_layout.setSpacing(10)
        
        # Language row
        lang_row = QHBoxLayout()
        lang_row.setSpacing(15)
        
        # Source language
        lang_row.addWidget(QLabel("From:"))
        self.source_lang_combo = QComboBox()
        self.populate_languages(self.source_lang_combo, True)
        self.source_lang_combo.setMinimumWidth(200)
        lang_row.addWidget(self.source_lang_combo)
        
        # Swap button
        self.swap_btn = QPushButton("⇄")
        self.swap_btn.setFixedSize(40, 35)
        self.swap_btn.setToolTip("Swap languages")
        self.swap_btn.clicked.connect(self.swap_languages)
        lang_row.addWidget(self.swap_btn)
        
        # Target language
        lang_row.addWidget(QLabel("To:"))
        self.target_lang_combo = QComboBox()
        self.populate_languages(self.target_lang_combo)
        self.target_lang_combo.setMinimumWidth(200)
        lang_row.addWidget(self.target_lang_combo)
        
        lang_row.addStretch()
        lang_layout.addLayout(lang_row)
        
        # Engine selection
        engine_row = QHBoxLayout()
        engine_row.setSpacing(15)
        engine_row.addWidget(QLabel("Engine:"))
        self.engine_combo = QComboBox()
        self.engine_combo.addItem("🌐 Google", RecognitionEngine.GOOGLE.value)
        self.engine_combo.addItem("💻 Vosk", RecognitionEngine.VOSK.value)
        self.engine_combo.addItem("🤖 Whisper", RecognitionEngine.WHISPER.value)
        self.engine_combo.currentIndexChanged.connect(self.on_engine_changed)
        engine_row.addWidget(self.engine_combo)
        
        engine_row.addWidget(QLabel("Mode:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Standard", "Simultaneous", "Universal", "Voice Clone"])
        self.mode_combo.currentTextChanged.connect(self.on_translation_mode_changed)
        engine_row.addWidget(self.mode_combo)
        
        engine_row.addStretch()
        lang_layout.addLayout(engine_row)
        
        layout.addWidget(lang_group)
        
        # Input/Output area
        io_splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Input area
        input_group = QGroupBox("🎙️ Input")
        input_layout = QVBoxLayout(input_group)
        
        self.input_text = QTextEdit()
        self.input_text.setPlaceholderText("🎤 Speak or type here...\n\nClick 'Start Listening' to begin continuous speech recognition.\nYour words will appear here in real-time.")
        self.input_text.textChanged.connect(self.update_word_count)
        input_layout.addWidget(self.input_text)
        
        io_splitter.addWidget(input_group)
        
        # Output area
        output_group = QGroupBox("🈯 Translation")
        output_layout = QVBoxLayout(output_group)
        
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setPlaceholderText("🌐 Translation will appear here...\n\nTranslations are processed in real-time through our async pipeline.")
        output_layout.addWidget(self.output_text)
        
        io_splitter.addWidget(output_group)
        
        # Set splitter proportions
        io_splitter.setSizes([300, 300])
        layout.addWidget(io_splitter, 1)
        
        self.main_tabs.addTab(translation_widget, "🌐 Translation")
    
    def setup_settings_tab(self):
        """Settings tab with organized options"""
        settings_widget = QWidget()
        layout = QVBoxLayout(settings_widget)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Audio settings
        audio_group = QGroupBox("🔊 Audio Settings")
        audio_layout = QVBoxLayout(audio_group)
        audio_layout.setSpacing(10)
        
        self.auto_speak = QCheckBox("🔊 Auto-speak translations")
        self.auto_speak.setChecked(config.get("auto_speak", True))
        self.auto_speak.stateChanged.connect(lambda: config.set("auto_speak", self.auto_speak.isChecked()))
        audio_layout.addWidget(self.auto_speak)
        
        self.show_conf = QCheckBox("🎯 Show confidence scores")
        self.show_conf.setChecked(config.get("show_confidence", True))
        self.show_conf.stateChanged.connect(lambda: config.set("show_confidence", self.show_conf.isChecked()))
        audio_layout.addWidget(self.show_conf)
        
        layout.addWidget(audio_group)
        
        # Advanced settings
        adv_group = QGroupBox("⚡ Advanced Settings")
        adv_layout = QVBoxLayout(adv_group)
        adv_layout.setSpacing(10)
        
        self.gpu_checkbox = QCheckBox("🚀 GPU Acceleration")
        self.gpu_checkbox.setChecked(config.get("use_gpu", True))
        self.gpu_checkbox.setEnabled(gpu_manager.is_gpu_available())
        self.gpu_checkbox.stateChanged.connect(self.on_gpu_toggled)
        adv_layout.addWidget(self.gpu_checkbox)
        
        self.conversation_mode_checkbox = QCheckBox("🗣️ Conversation Mode")
        self.conversation_mode_checkbox.setChecked(config.get("conversation_mode_enabled", False))
        self.conversation_mode_checkbox.stateChanged.connect(self.on_conversation_mode_toggled)
        adv_layout.addWidget(self.conversation_mode_checkbox)
        
        self.slang_checkbox = QCheckBox("💬 Slang & Autocorrect")
        self.slang_checkbox.setChecked(config.get("slang_translation_enabled", True))
        self.slang_checkbox.stateChanged.connect(self.on_slang_toggled)
        adv_layout.addWidget(self.slang_checkbox)
        
        layout.addWidget(adv_group)
        
        # Theme settings
        theme_group = QGroupBox("🎨 Appearance")
        theme_layout = QVBoxLayout(theme_group)
        theme_layout.setSpacing(10)
        
        theme_row = QHBoxLayout()
        theme_row.addWidget(QLabel("Theme:"))
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark", "Light"])
        self.theme_combo.setCurrentText(config.get("theme", "dark").title())
        self.theme_combo.currentTextChanged.connect(self.on_theme_changed)
        theme_row.addWidget(self.theme_combo)
        theme_row.addStretch()
        theme_layout.addLayout(theme_row)
        
        layout.addWidget(theme_group)
        
        layout.addStretch()
        self.main_tabs.addTab(settings_widget, "⚙️ Settings")
    
    def setup_history_tab(self):
        """History tab with search and management"""
        history_widget = QWidget()
        layout = QVBoxLayout(history_widget)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Search bar
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("🔍 Search:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search translation history...")
        self.search_input.textChanged.connect(self.search_history)
        search_layout.addWidget(self.search_input)
        
        # Clear button
        clear_btn = QPushButton("🗑️ Clear")
        clear_btn.clicked.connect(self.clear_history)
        search_layout.addWidget(clear_btn)
        
        # Export button
        export_btn = QPushButton("💾 Export")
        export_btn.clicked.connect(self.export_history)
        search_layout.addWidget(export_btn)
        
        layout.addLayout(search_layout)
        
        # History list
        self.history_list = QListWidget()
        self.history_list.itemDoubleClicked.connect(self.load_history_item)
        layout.addWidget(self.history_list)
        
        self.main_tabs.addTab(history_widget, "📜 History")
    
    def setup_models_tab(self):
        """Models tab for managing AI models"""
        models_widget = QWidget()
        layout = QVBoxLayout(models_widget)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Model management buttons
        btn_layout = QHBoxLayout()
        
        models_btn = QPushButton("📥 Manage Models")
        models_btn.clicked.connect(self.show_models)
        btn_layout.addWidget(models_btn)
        
        voice_btn = QPushButton("🎙️ Voice Models")
        voice_btn.clicked.connect(self.show_rvc_models)
        btn_layout.addWidget(voice_btn)
        
        platforms_btn = QPushButton("🔗 Platform Integrations")
        platforms_btn.clicked.connect(self.show_platforms)
        btn_layout.addWidget(platforms_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        # Model status
        status_group = QGroupBox("📊 Model Status")
        status_layout = QVBoxLayout(status_group)
        
        self.model_status = QLabel("Loading model information...")
        self.model_status.setWordWrap(True)
        status_layout.addWidget(self.model_status)
        
        layout.addWidget(status_group)
        layout.addStretch()
        
        self.main_tabs.addTab(models_widget, "🤖 Models")
    
    def setup_control_panel(self, parent_layout):
        """Control panel with main action buttons"""
        control_widget = QWidget()
        control_layout = QVBoxLayout(control_widget)
        control_layout.setSpacing(15)
        
        # Main control buttons
        main_controls = QHBoxLayout()
        main_controls.setSpacing(15)
        
        # Start/Stop listening button
        self.listen_btn = QPushButton("🎤 Start Listening")
        self.listen_btn.setMinimumHeight(60)
        self.listen_btn.setStyleSheet("""
            QPushButton {
                font-weight: 700;
                font-size: 16px;
                padding: 15px 30px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #4CAF50, stop:1 #388E3C);
                color: white;
                border: none;
                border-radius: 15px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #5FD068, stop:1 #4CAF50);
            }
            QPushButton:pressed {
                background: #2E7D32;
            }
        """)
        self.listen_btn.clicked.connect(self.toggle_listening)
        main_controls.addWidget(self.listen_btn)
        
        # Secondary controls
        secondary_controls = QHBoxLayout()
        secondary_controls.setSpacing(10)
        
        self.translate_btn = QPushButton("🔄 Translate")
        self.translate_btn.clicked.connect(self.translate_manual)
        secondary_controls.addWidget(self.translate_btn)
        
        self.speak_btn = QPushButton("🔊 Speak")
        self.speak_btn.clicked.connect(self.speak_output)
        secondary_controls.addWidget(self.speak_btn)
        
        self.stop_btn = QPushButton("🔇 Stop")
        self.stop_btn.clicked.connect(lambda: tts_manager.stop())
        secondary_controls.addWidget(self.stop_btn)
        
        self.source_btn = QPushButton("🎧 System Audio")
        self.source_btn.clicked.connect(self.toggle_source)
        secondary_controls.addWidget(self.source_btn)
        
        self.overlay_btn = QPushButton("👁️ Overlay")
        self.overlay_btn.clicked.connect(self.toggle_overlay)
        secondary_controls.addWidget(self.overlay_btn)
        
        secondary_controls.addStretch()
        
        # Word count
        self.word_count = QLabel("0 words")
        self.word_count.setStyleSheet("color: #9aa0a6; font-size: 14px; font-weight: 600;")
        secondary_controls.addWidget(self.word_count)
        
        control_layout.addLayout(main_controls)
        control_layout.addLayout(secondary_controls)
        
        parent_layout.addWidget(control_widget)
    
    def setup_menu_bar(self):
        """Create organized menu bar"""
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
        
        # Help menu
        help_menu = menubar.addMenu("❓ Help")
        
        help_action = QAction("📖 Show Help", self)
        help_action.setShortcut("F1")
        help_action.triggered.connect(self.show_help)
        help_menu.addAction(help_action)
    
    def setup_shortcuts(self):
        """Setup keyboard shortcuts"""
        QShortcut(QKeySequence("F1"), self, self.show_help)
        QShortcut(QKeySequence("Ctrl+L"), self, self.toggle_listening)
        QShortcut(QKeySequence("Ctrl+T"), self, self.translate_manual)
        QShortcut(QKeySequence("Ctrl+S"), self, self.speak_output)
        QShortcut(QKeySequence("Ctrl+O"), self, self.toggle_overlay)
        QShortcut(QKeySequence("Ctrl+D"), self, self.toggle_theme)
        QShortcut(QKeySequence("Ctrl+Q"), self, self.close)
    
    def show_error_dialog(self, title, message):
        """Show error dialog with proper formatting"""
        msg = QMessageBox(self)
        msg.setWindowTitle(title)
        msg.setText(message)
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.exec()
    
    def show_info_dialog(self, title, message):
        """Show info dialog with proper formatting"""
        msg = QMessageBox(self)
        msg.setWindowTitle(title)
        msg.setText(message)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.exec()
    
    # Event handlers with proper error handling
    def populate_languages(self, combo, include_auto=False):
        """Populate language combo box"""
        try:
            if include_auto:
                combo.addItem("🔍 Auto", "auto")
            langs = sorted([(n.title(), c) for n, c in GOOGLE_LANGUAGES_TO_CODES.items()], key=lambda x: x[0])
            for name, code in langs:
                combo.addItem(name, code)
        except Exception as e:
            log.error(f"Error populating languages: {e}")
            self.show_error_dialog("Language Error", f"Failed to load languages:\n{str(e)}")
    
    def load_settings(self):
        """Load saved settings"""
        try:
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
            
        except Exception as e:
            log.error(f"Error loading settings: {e}")
            self.show_error_dialog("Settings Error", f"Failed to load settings:\n{str(e)}")
    
    def on_engine_changed(self):
        """Handle engine change"""
        try:
            engine_val = self.engine_combo.currentData()
            self.recognition_engine = RecognitionEngine(engine_val)
            config.set("recognition_engine", engine_val)
            
            if self.recognition_thread and self.recognition_thread.isRunning():
                self.stop_listening()
                QTimer.singleShot(500, self.start_listening)
                
            self.statusBar().showMessage(f"✅ Engine changed to {self.engine_combo.currentText()}", 3000)
        except Exception as e:
            log.error(f"Error changing engine: {e}")
            self.show_error_dialog("Engine Error", f"Failed to change engine:\n{str(e)}")
    
    def on_gpu_toggled(self):
        """Handle GPU toggle"""
        try:
            use_gpu = self.gpu_checkbox.isChecked()
            config.set("use_gpu", use_gpu)
            whisper_manager.set_device(use_gpu)
            device = whisper_manager.device
            
            # Update GPU status indicator
            gpu_color = "#4CAF50" if use_gpu and gpu_manager.is_gpu_available() else "#FFC107"
            self.gpu_status.setText(f"🚀 {device.upper()}")
            self.gpu_status.setStyleSheet(f"""
                QLabel {{
                    color: {gpu_color};
                    font-weight: 600;
                    font-size: 13px;
                    padding: 8px 15px;
                    background: rgba({int(gpu_color[1:3], 16)},{int(gpu_color[3:5], 16)},{int(gpu_color[5:7], 16)},0.1);
                    border-radius: 8px;
                    border: 2px solid {gpu_color};
                }}
            """)
            
            if use_gpu and gpu_manager.is_gpu_available():
                self.statusBar().showMessage(f"✅ GPU acceleration ENABLED - Using {device.upper()}", 4000)
            else:
                self.statusBar().showMessage(f"⚠️ GPU acceleration disabled - Using {device.upper()}", 4000)
        except Exception as e:
            log.error(f"Error toggling GPU: {e}")
            self.show_error_dialog("GPU Error", f"Failed to toggle GPU:\n{str(e)}")
    
    def on_conversation_mode_toggled(self):
        """Handle conversation mode toggle"""
        try:
            enabled = self.conversation_mode_checkbox.isChecked()
            config.set("conversation_mode_enabled", enabled)
            
            if enabled:
                src_lang = self.source_lang_combo.currentData()
                tgt_lang = self.target_lang_combo.currentData()
                
                if src_lang == "auto":
                    src_lang = "en"
                
                auto_mode = self.auto_mode_checkbox.isChecked()
                conversation_mode.enable(src_lang, tgt_lang, auto_mode)
                
                self.statusBar().showMessage(
                    f"🗣️ Conversation Mode ENABLED: {src_lang} ↔ {tgt_lang}", 4000
                )
            else:
                conversation_mode.disable()
                self.statusBar().showMessage("Conversation Mode disabled", 3000)
        except Exception as e:
            log.error(f"Error toggling conversation mode: {e}")
            self.show_error_dialog("Conversation Mode Error", f"Failed to toggle conversation mode:\n{str(e)}")
    
    def on_slang_toggled(self):
        """Handle slang translation toggle"""
        try:
            enabled = self.slang_checkbox.isChecked()
            config.set("slang_translation_enabled", enabled)
            
            translator.use_slang_expansion = enabled
            translator.use_autocorrect = enabled
            
            if enabled:
                self.statusBar().showMessage("💬 Slang translation & autocorrect ENABLED", 3000)
            else:
                self.statusBar().showMessage("Slang translation & autocorrect disabled", 3000)
        except Exception as e:
            log.error(f"Error toggling slang: {e}")
            self.show_error_dialog("Slang Error", f"Failed to toggle slang translation:\n{str(e)}")
    
    def on_theme_changed(self, theme):
        """Handle theme change"""
        try:
            theme = theme.lower()
            config.set("theme", theme)
            self.apply_theme(theme)
            self.statusBar().showMessage(f"✅ Theme changed to {theme.title()}", 2000)
        except Exception as e:
            log.error(f"Error changing theme: {e}")
            self.show_error_dialog("Theme Error", f"Failed to change theme:\n{str(e)}")
    
    def on_translation_mode_changed(self, mode_text):
        """Handle translation mode change"""
        try:
            mode_map = {
                "Standard": TranslationMode.STANDARD,
                "Simultaneous": TranslationMode.SIMULTANEOUS,
                "Universal": TranslationMode.UNIVERSAL,
                "Voice Clone": TranslationMode.VOICE_DUPLICATION
            }
            
            selected_mode = mode_map.get(mode_text, TranslationMode.STANDARD)
            translation_mode_manager.set_mode(selected_mode)
            
            if selected_mode == TranslationMode.VOICE_DUPLICATION:
                if voice_duplication.get_current_model():
                    voice_duplication.enable()
                else:
                    self.show_info_dialog(
                        "Voice Clone Mode",
                        "No voice model selected. Please add and activate a voice model in Voice Models manager."
                    )
            
            self.translation_mode = mode_text
            self.statusBar().showMessage(f"✅ Translation mode changed to: {mode_text}", 3000)
        except Exception as e:
            log.error(f"Error changing translation mode: {e}")
            self.show_error_dialog("Translation Mode Error", f"Failed to change translation mode:\n{str(e)}")
    
    def swap_languages(self):
        """Swap source and target languages"""
        try:
            if self.source_lang_combo.currentData() == "auto":
                self.statusBar().showMessage("⚠️ Cannot swap with auto-detect enabled", 3000)
                return
            
            src_idx = self.source_lang_combo.currentIndex()
            tgt_idx = self.target_lang_combo.currentIndex()
            
            # Swap the selections
            self.source_lang_combo.setCurrentIndex(tgt_idx + 1)
            self.target_lang_combo.setCurrentIndex(src_idx - 1)
            
            src_lang = self.source_lang_combo.currentText()
            tgt_lang = self.target_lang_combo.currentText()
            self.statusBar().showMessage(f"⇄ Languages swapped: {src_lang} → {tgt_lang}", 2000)
        except Exception as e:
            log.error(f"Error swapping languages: {e}")
            self.show_error_dialog("Language Swap Error", f"Failed to swap languages:\n{str(e)}")
    
    def update_word_count(self):
        """Update word count display"""
        try:
            text = self.input_text.toPlainText()
            words = len(text.split()) if text.strip() else 0
            self.word_count.setText(f"{words} words")
        except Exception as e:
            log.error(f"Error updating word count: {e}")
    
    def toggle_listening(self):
        """Toggle listening state"""
        try:
            if self.is_listening:
                self.stop_listening()
            else:
                self.start_listening()
        except Exception as e:
            log.error(f"Error toggling listening: {e}")
            self.show_error_dialog("Listening Error", f"Failed to toggle listening:\n{str(e)}")
    
    def start_listening(self):
        """Start continuous listening"""
        try:
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
            
            self.is_listening = True
            self.listen_btn.setText("⏹️ Stop Listening")
            self.listen_btn.setStyleSheet("""
                QPushButton {
                    font-weight: 700;
                    font-size: 16px;
                    padding: 15px 30px;
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #F44336, stop:1 #D32F2F);
                    color: white;
                    border: none;
                    border-radius: 15px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #FF5252, stop:1 #F44336);
                }
                QPushButton:pressed {
                    background: #B71C1C;
                }
            """)
            self.statusBar().showMessage(f"🎙️ Continuous listening active ({self.recognition_engine.value} engine)", 5000)
        except Exception as e:
            log.error(f"Error starting listening: {e}")
            self.show_error_dialog("Listening Start Error", f"Failed to start listening:\n{str(e)}")
    
    def stop_listening(self):
        """Stop continuous listening"""
        try:
            if self.recognition_thread:
                self.recognition_thread.stop()
                self.recognition_thread.wait()
                self.recognition_thread = None
            
            self.is_listening = False
            self.listen_btn.setText("🎤 Start Listening")
            self.listen_btn.setStyleSheet("""
                QPushButton {
                    font-weight: 700;
                    font-size: 16px;
                    padding: 15px 30px;
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #4CAF50, stop:1 #388E3C);
                    color: white;
                    border: none;
                    border-radius: 15px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #5FD068, stop:1 #4CAF50);
                }
                QPushButton:pressed {
                    background: #2E7D32;
                }
            """)
            self.statusBar().showMessage("Stopped listening", 3000)
            self.perf_label.setText("⚡ Performance: Idle")
        except Exception as e:
            log.error(f"Error stopping listening: {e}")
            self.show_error_dialog("Listening Stop Error", f"Failed to stop listening:\n{str(e)}")
    
    def toggle_source(self):
        """Toggle audio source"""
        try:
            self.source_type = "system" if self.source_type == "microphone" else "microphone"
            self.source_btn.setText("🎤 Microphone" if self.source_type == "system" else "🎧 System Audio")
            
            source_name = "🎤 Microphone" if self.source_type == "microphone" else "🎧 System Audio"
            self.statusBar().showMessage(f"⇄ Switched to {source_name}", 2000)
            
            # Restart listening if active
            if self.is_listening:
                self.statusBar().showMessage(f"↻ Restarting with {source_name}...", 2000)
                self.stop_listening()
                QTimer.singleShot(500, self.start_listening)
        except Exception as e:
            log.error(f"Error toggling source: {e}")
            self.show_error_dialog("Source Toggle Error", f"Failed to toggle audio source:\n{str(e)}")
    
    def update_status_safe(self, message):
        """Thread-safe status update"""
        try:
            QMetaObject.invokeMethod(
                self.statusBar(), "showMessage",
                Qt.ConnectionType.QueuedConnection,
                Q_ARG(str, message)
            )
        except Exception as e:
            log.error(f"Error updating status: {e}")
    
    def handle_recognition_error(self, error_msg):
        """Handle recognition errors"""
        try:
            self.show_error_dialog("Recognition Error", error_msg)
            self.stop_listening()
        except Exception as e:
            log.error(f"Error handling recognition error: {e}")
    
    def update_performance(self, perf_data):
        """Update performance indicators"""
        try:
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
                    padding: 8px 15px;
                    background: rgba({int(color[1:3], 16)},{int(color[3:5], 16)},{int(color[5:7], 16)},0.1);
                    border-radius: 8px;
                    border: 2px solid {color};
                }}
            """)
        except Exception as e:
            log.error(f"Error updating performance: {e}")
    
    def handle_phrase(self, phrase, confidence):
        """Handle detected phrase"""
        try:
            if not phrase.strip():
                return
            
            cursor = self.input_text.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            timestamp = datetime.now().strftime("%H:%M:%S")
            conf_str = f" [{confidence:.0%}]" if config.get("show_confidence") else ""
            cursor.insertText(f"[{timestamp}]{conf_str} {phrase}\n")
            self.input_text.setTextCursor(cursor)
            self.input_text.ensureCursorVisible()
            
            if self.translation_mode in ["Real-time", "Continuous"]:
                # Async translation - non-blocking
                self.translate_phrase_async(phrase, confidence)
        except Exception as e:
            log.error(f"Error handling phrase: {e}")
            self.show_error_dialog("Phrase Error", f"Failed to handle phrase:\n{str(e)}")
    
    def translate_phrase_async(self, phrase, speech_conf=1.0):
        """Async translation with error handling"""
        try:
            src_lang = self.source_lang_combo.currentData()
            tgt_lang = self.target_lang_combo.currentData()
            
            # Auto-detect if needed
            if src_lang == "auto":
                try:
                    detections = detect_langs(phrase)
                    src_lang = detections[0].lang if detections else "en"
                except:
                    src_lang = "en"
            
            def on_translation_complete(result):
                try:
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
                except Exception as e:
                    log.error(f"Error in translation callback: {e}")
            
            # Submit async translation
            translator.translate_async(phrase, src_lang, tgt_lang, on_translation_complete)
        except Exception as e:
            log.error(f"Error in async translation: {e}")
            self.show_error_dialog("Translation Error", f"Failed to translate phrase:\n{str(e)}")
    
    def translate_manual(self):
        """Manual translation with error handling"""
        try:
            text = self.input_text.toPlainText().strip()
            if not text:
                self.statusBar().showMessage("No text to translate", 3000)
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
        except Exception as e:
            log.error(f"Error in manual translation: {e}")
            self.show_error_dialog("Manual Translation Error", f"Failed to translate text:\n{str(e)}")
    
    def speak_output(self):
        """Speak output text"""
        try:
            text = self.output_text.toPlainText().strip()
            if not text:
                self.statusBar().showMessage("No text to speak", 3000)
                return
            
            import re
            text = re.sub(r'\[.*?\]\s*', '', text)
            lang = self.target_lang_combo.currentData()
            tts_manager.speak(text, lang)
        except Exception as e:
            log.error(f"Error speaking output: {e}")
            self.show_error_dialog("Speech Error", f"Failed to speak text:\n{str(e)}")
    
    def toggle_overlay(self):
        """Toggle overlay visibility"""
        try:
            is_visible = not self.overlay.isVisible()
            self.overlay.setVisible(is_visible)
            config.set("overlay_visible", is_visible)
            
            status = "👁️ Overlay shown" if is_visible else "🚫 Overlay hidden"
            self.statusBar().showMessage(status, 2000)
        except Exception as e:
            log.error(f"Error toggling overlay: {e}")
            self.show_error_dialog("Overlay Error", f"Failed to toggle overlay:\n{str(e)}")
    
    def toggle_theme(self):
        """Toggle theme"""
        try:
            current = config.get("theme", "dark")
            new = "light" if current == "dark" else "dark"
            config.set("theme", new)
            self.apply_theme(new)
            
            theme_name = "🌙 Dark Mode" if new == "dark" else "☀️ Light Mode"
            self.statusBar().showMessage(f"✅ Switched to {theme_name}", 2000)
        except Exception as e:
            log.error(f"Error toggling theme: {e}")
            self.show_error_dialog("Theme Error", f"Failed to toggle theme:\n{str(e)}")
    
    def apply_theme(self, theme):
        """Apply theme with error handling"""
        try:
            if theme == "dark":
                # Dark theme
                self.setStyleSheet("""
                    QMainWindow, QWidget {
                        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                            stop:0 #0f0f14, stop:1 #1a1a20);
                        color: #e8eaed;
                        font-family: "Segoe UI", "SF Pro Display", -apple-system, system-ui, sans-serif;
                    }
                    QGroupBox {
                        border: 2px solid rgba(255,255,255,0.1);
                        border-radius: 12px;
                        margin-top: 10px;
                        padding-top: 15px;
                        background: rgba(255,255,255,0.02);
                        font-size: 14px;
                        font-weight: 600;
                    }
                    QGroupBox::title {
                        left: 15px;
                        padding: 0 10px;
                        color: #82c8ff;
                        font-weight: 700;
                        font-size: 15px;
                    }
                    QTextEdit, QListWidget, QLineEdit {
                        background: rgba(28,28,35,0.8);
                        border: 2px solid rgba(255,255,255,0.1);
                        border-radius: 10px;
                        padding: 12px;
                        selection-background-color: #82c8ff;
                        selection-color: #0f0f14;
                        font-size: 14px;
                        line-height: 1.6;
                    }
                    QTextEdit:focus, QLineEdit:focus {
                        border: 2px solid #82c8ff;
                        background: rgba(28,28,35,0.9);
                    }
                    QPushButton {
                        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                            stop:0 rgba(60,60,70,0.9), stop:1 rgba(45,45,55,0.9));
                        border: 2px solid rgba(255,255,255,0.15);
                        border-radius: 8px;
                        padding: 10px 20px;
                        font-weight: 600;
                        font-size: 14px;
                        color: #e8eaed;
                    }
                    QPushButton:hover {
                        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                            stop:0 rgba(75,75,85,0.95), stop:1 rgba(60,60,70,0.95));
                        border: 2px solid #82c8ff;
                    }
                    QPushButton:pressed {
                        background: rgba(45,45,55,1);
                        border: 2px solid #5fa8d3;
                    }
                    QComboBox {
                        background: rgba(28,28,35,0.8);
                        border: 2px solid rgba(255,255,255,0.1);
                        border-radius: 8px;
                        padding: 8px 12px;
                        font-size: 14px;
                        min-height: 20px;
                    }
                    QComboBox:hover {
                        border: 2px solid #82c8ff;
                        background: rgba(28,28,35,0.9);
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
                        font-size: 14px;
                    }
                    QCheckBox::indicator {
                        width: 20px;
                        height: 20px;
                        border-radius: 6px;
                        border: 2px solid rgba(255,255,255,0.2);
                        background: rgba(28,28,35,0.8);
                    }
                    QCheckBox::indicator:hover {
                        border: 2px solid #82c8ff;
                        background: rgba(28,28,35,0.9);
                    }
                    QCheckBox::indicator:checked {
                        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                            stop:0 #82c8ff, stop:1 #5fa8d3);
                        border-color: #82c8ff;
                    }
                    QStatusBar {
                        background: rgba(20,20,26,0.95);
                        border-top: 2px solid rgba(255,255,255,0.1);
                        color: #b8bbbe;
                        font-size: 13px;
                        padding: 8px;
                    }
                    QLabel {
                        color: #e8eaed;
                        font-size: 14px;
                    }
                """)
            else:
                # Light theme
                self.setStyleSheet("""
                    QMainWindow, QWidget {
                        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                            stop:0 #fafafa, stop:1 #f0f0f5);
                        color: #1f1f1f;
                        font-family: "Segoe UI", "SF Pro Display", -apple-system, system-ui, sans-serif;
                    }
                    QGroupBox {
                        border: 2px solid rgba(0,0,0,0.1);
                        border-radius: 12px;
                        margin-top: 10px;
                        padding-top: 15px;
                        background: rgba(255,255,255,0.8);
                        font-size: 14px;
                        font-weight: 600;
                    }
                    QGroupBox::title {
                        left: 15px;
                        padding: 0 10px;
                        color: #1967d2;
                        font-weight: 700;
                        font-size: 15px;
                    }
                    QTextEdit, QListWidget, QLineEdit {
                        background: rgba(255,255,255,0.9);
                        border: 2px solid rgba(0,0,0,0.1);
                        border-radius: 10px;
                        padding: 12px;
                        selection-background-color: #1967d2;
                        selection-color: white;
                        font-size: 14px;
                        line-height: 1.6;
                    }
                    QTextEdit:focus, QLineEdit:focus {
                        border: 2px solid #1967d2;
                        background: white;
                    }
                    QPushButton {
                        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                            stop:0 rgba(255,255,255,0.95), stop:1 rgba(245,245,250,0.95));
                        border: 2px solid rgba(0,0,0,0.15);
                        border-radius: 8px;
                        padding: 10px 20px;
                        font-weight: 600;
                        font-size: 14px;
                        color: #1f1f1f;
                    }
                    QPushButton:hover {
                        background: white;
                        border: 2px solid #1967d2;
                        color: #1967d2;
                    }
                    QPushButton:pressed {
                        background: rgba(245,245,250,1);
                        border: 2px solid #1557b0;
                    }
                    QComboBox {
                        background: rgba(255,255,255,0.9);
                        border: 2px solid rgba(0,0,0,0.1);
                        border-radius: 8px;
                        padding: 8px 12px;
                        font-size: 14px;
                    }
                    QComboBox:hover {
                        border: 2px solid #1967d2;
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
                        border-top: 2px solid rgba(0,0,0,0.1);
                        color: #5f6368;
                        font-size: 13px;
                        padding: 8px;
                    }
                """)
            
            # Update overlay style
            self.overlay.apply_style()
        except Exception as e:
            log.error(f"Error applying theme: {e}")
            self.show_error_dialog("Theme Error", f"Failed to apply theme:\n{str(e)}")
    
    def refresh_history_throttled(self):
        """Throttled history refresh"""
        try:
            now = time.time()
            if now - self.last_history_refresh > self.history_refresh_throttle:
                self.refresh_history()
                self.last_history_refresh = now
        except Exception as e:
            log.error(f"Error refreshing history: {e}")
    
    def refresh_history(self, search=""):
        """Refresh history list"""
        try:
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
        except Exception as e:
            log.error(f"Error refreshing history: {e}")
            self.show_error_dialog("History Error", f"Failed to refresh history:\n{str(e)}")
    
    def search_history(self):
        """Search history"""
        try:
            self.refresh_history(self.search_input.text())
        except Exception as e:
            log.error(f"Error searching history: {e}")
    
    def load_history_item(self, item):
        """Load history item"""
        try:
            data = item.data(Qt.ItemDataRole.UserRole)
            if data:
                self.input_text.setPlainText(data['source_text'])
                self.output_text.setPlainText(data['translated_text'])
        except Exception as e:
            log.error(f"Error loading history item: {e}")
    
    def export_history(self):
        """Export history"""
        try:
            default_filename = f"translator_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            filename, _ = QFileDialog.getSaveFileName(
                self, 
                "💾 Export Translation History", 
                str(BASE_DIR / default_filename), 
                "Text Files (*.txt);;All Files (*)"
            )
            if filename:
                db.export_history(filename)
                with open(filename, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    count = len([l for l in lines if l.startswith('[')])
                
                self.show_info_dialog(
                    "✅ Export Successful",
                    f"Successfully exported {count} translations to:\n\n{filename}"
                )
                self.statusBar().showMessage(f"✅ Exported {count} translations", 3000)
        except Exception as e:
            log.error(f"Error exporting history: {e}")
            self.show_error_dialog("Export Error", f"Failed to export history:\n{str(e)}")
    
    def clear_history(self):
        """Clear history"""
        try:
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
        except Exception as e:
            log.error(f"Error clearing history: {e}")
            self.show_error_dialog("Clear History Error", f"Failed to clear history:\n{str(e)}")
    
    def show_models(self):
        """Show model manager"""
        try:
            dialog = ModelManagerDialog(self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                pass
        except Exception as e:
            log.error(f"Error showing models: {e}")
            self.show_error_dialog("Model Manager Error", f"Failed to open model manager:\n{str(e)}")
    
    def show_platforms(self):
        """Show platform integrations"""
        try:
            from .platform_integrations_dialog import PlatformIntegrationsDialog
            dialog = PlatformIntegrationsDialog(self)
            dialog.exec()
        except Exception as e:
            log.error(f"Error showing platforms: {e}")
            self.show_error_dialog("Platform Error", f"Failed to open platform integrations:\n{str(e)}")
    
    def show_rvc_models(self):
        """Show RVC models"""
        try:
            from .rvc_model_dialog import RVCModelDialog
            dialog = RVCModelDialog(self)
            dialog.exec()
        except Exception as e:
            log.error(f"Error showing RVC models: {e}")
            self.show_error_dialog("RVC Model Error", f"Failed to open RVC models:\n{str(e)}")
    
    def show_help(self):
        """Show help dialog"""
        try:
            help_text = f"""
🌍 Universal Live Translator — Professional Edition v4.5

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✨ MAIN FEATURES
• 🎙️ Continuous listening - speak naturally without stopping
• 🌐 Real-time translation with multiple engines
• 📺 Netflix-style overlay for subtitles
• 🚀 GPU acceleration for 10-20x faster processing
• 🗣️ Conversation mode for bidirectional translation
• 💬 Slang and autocorrect support

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎮 HOW TO USE
1. Select your source and target languages
2. Choose your preferred recognition engine
3. Click "Start Listening" to begin
4. Speak naturally - no need to pause
5. Translations appear in real-time

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⌨️ KEYBOARD SHORTCUTS
• F1 → Show this help
• Ctrl+L → Start/stop listening
• Ctrl+T → Manual translate
• Ctrl+S → Speak output
• Ctrl+O → Toggle overlay
• Ctrl+D → Toggle theme
• Ctrl+Q → Quit

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚙️ SETTINGS
• Use the Settings tab to configure audio, GPU, and appearance
• Enable conversation mode for automatic bidirectional translation
• Adjust confidence display and auto-speak options

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🤖 MODELS
• Use the Models tab to download and manage AI models
• Whisper models for offline speech recognition
• Voice models for voice cloning features

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📜 HISTORY
• View and search your translation history
• Export translations to text files
• Double-click to reload previous translations

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 TIPS
• Use GPU acceleration for better performance
• Enable conversation mode for meetings
• Use the overlay for presentations
• Check the History tab for past translations

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Enjoy your professional-grade translator! 🚀
"""
            msg = QMessageBox(self)
            msg.setWindowTitle("✨ Help — Universal Live Translator v4.5")
            msg.setText(help_text)
            msg.setIcon(QMessageBox.Icon.Information)
            msg.setStyleSheet("QLabel{min-width: 600px; font-family: monospace;}")
            msg.exec()
        except Exception as e:
            log.error(f"Error showing help: {e}")
            self.show_error_dialog("Help Error", f"Failed to show help:\n{str(e)}")
    
    def closeEvent(self, event):
        """Handle application close"""
        try:
            config.set("source_language", self.source_lang_combo.currentData())
            config.set("target_language", self.target_lang_combo.currentData())
            
            if self.recognition_thread:
                self.recognition_thread.stop()
                self.recognition_thread.wait()
            
            tts_manager.shutdown()
            audio_device_manager.cleanup()
            self.overlay.close()
            event.accept()
        except Exception as e:
            log.error(f"Error during close: {e}")
            event.accept()