"""Model manager dialog for downloading and managing models"""
import logging
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from config.constants import WHISPER_MODELS, VOSK_MODELS
from models import vosk_manager, whisper_manager

log = logging.getLogger("Translator")

class ModelManagerDialog(QDialog):
    """Professional model download and management dialog with Material Design 3"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📥 Model Manager — Universal Live Translator")
        self.setMinimumWidth(750)
        self.setMinimumHeight(550)
        self.setup_ui()
        # Apply professional styling
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
        """)
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        tabs = QTabWidget()
        
        # ===== WHISPER TAB =====
        whisper_tab = QWidget()
        whisper_layout = QVBoxLayout(whisper_tab)
        
        whisper_info = QLabel(
            "Whisper models download automatically on first use.\\n"
            "Models are cached in your home directory (~/.cache/whisper)."
        )
        whisper_info.setWordWrap(True)
        whisper_layout.addWidget(whisper_info)
        
        whisper_group = QGroupBox("Available Whisper Models")
        whisper_group_layout = QVBoxLayout()
        
        for model in WHISPER_MODELS:
            model_row = QHBoxLayout()
            label = QLabel(f"{model.title()}")
            model_row.addWidget(label)
            
            size_label = QLabel()
            if model == "tiny":
                size_label.setText("~75 MB")
            elif model == "base":
                size_label.setText("~150 MB")
            elif model == "small":
                size_label.setText("~500 MB")
            elif model == "medium":
                size_label.setText("~1.5 GB")
            elif model == "large":
                size_label.setText("~3 GB")
            model_row.addWidget(size_label)
            
            model_row.addStretch()
            
            download_btn = QPushButton("📥 Download")
            download_btn.clicked.connect(lambda checked, m=model: self.download_whisper_model(m))
            model_row.addWidget(download_btn)
            
            whisper_group_layout.addLayout(model_row)
        
        whisper_group.setLayout(whisper_group_layout)
        whisper_layout.addWidget(whisper_group)
        
        current_device = QLabel(f"Current Device: {whisper_manager.device}")
        whisper_layout.addWidget(current_device)
        
        whisper_layout.addStretch()
        tabs.addTab(whisper_tab, "Whisper Models")
        
        # ===== VOSK TAB =====
        vosk_tab = QWidget()
        vosk_layout = QVBoxLayout(vosk_tab)
        
        vosk_info = QLabel(
            f"Vosk models are downloaded to: {VOSK_MODELS_DIR}\\n"
            "These are offline speech recognition models."
        )
        vosk_info.setWordWrap(True)
        vosk_layout.addWidget(vosk_info)
        
        vosk_group = QGroupBox("Available Vosk Models")
        vosk_group_layout = QVBoxLayout()
        
        for lang_code, url in VOSK_MODELS.items():
            model_row = QHBoxLayout()
            
            lang_name = {"en": "English", "fr": "French", "es": "Spanish", "de": "German"}.get(lang_code, lang_code)
            label = QLabel(f"{lang_name} ({lang_code})")
            model_row.addWidget(label)
            
            has_model = vosk_manager.has_model(lang_code)
            status = QLabel("✅ Installed" if has_model else "❌ Not installed")
            model_row.addWidget(status)
            
            model_row.addStretch()
            
            if not has_model:
                download_btn = QPushButton("📥 Download (~50 MB)")
                download_btn.clicked.connect(lambda checked, lc=lang_code: self.download_vosk_model(lc))
                model_row.addWidget(download_btn)
            
            vosk_group_layout.addLayout(model_row)
        
        vosk_group.setLayout(vosk_group_layout)
        vosk_layout.addWidget(vosk_group)
        
        vosk_layout.addStretch()
        tabs.addTab(vosk_tab, "Vosk Models")
        
        layout.addWidget(tabs)
        
        # Professional close button
        close_btn = QPushButton("✔ Done")
        close_btn.clicked.connect(self.accept)
        close_btn.setStyleSheet("""
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
        """)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignCenter)
    
    def download_whisper_model(self, model_name):
        reply = QMessageBox.question(
            self,
            "Download Whisper Model",
            f"Download {model_name} model?\\n\\nThe model will download automatically on first use.\\n"
            f"You can test it by selecting '{model_name}' in Settings and using Whisper engine.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Create progress dialog
            progress = QProgressDialog(f"Downloading Whisper {model_name} model...", None, 0, 0, self)
            progress.setWindowTitle("Downloading")
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.show()
            QApplication.processEvents()
            
            # Download in thread to avoid blocking UI
            success = whisper_manager.load_model(model_name)
            
            progress.close()
            
            if success:
                QMessageBox.information(self, "Success", f"Whisper {model_name} model loaded successfully!")
            else:
                QMessageBox.warning(self, "Error", f"Failed to download {model_name} model. Check logs for details.")
    
    def download_vosk_model(self, lang_code):
        reply = QMessageBox.question(
            self,
            "Download Vosk Model",
            f"Download Vosk model for {lang_code}?\\n\\nSize: ~50 MB",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            progress = QProgressDialog(f"Downloading Vosk {lang_code} model...", "Cancel", 0, 100, self)
            progress.setWindowTitle("Downloading")
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.show()
            
            def update_progress(pct):
                progress.setValue(int(pct * 100))
                QApplication.processEvents()
            
            success = vosk_manager.download_model(lang_code, update_progress)
            
            progress.close()
            
            if success:
                QMessageBox.information(self, "Success", f"Vosk {lang_code} model downloaded successfully!")
                # Refresh the dialog
                self.close()
                new_dialog = ModelManagerDialog(self.parent())
                new_dialog.exec()
            else:
                QMessageBox.warning(self, "Error", f"Failed to download {lang_code} model. Check logs for details.")

