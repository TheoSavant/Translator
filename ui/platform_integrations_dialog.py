"""Platform Integrations Dialog for Discord, Zoom, Teams, etc."""
import logging
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from core.platform_integrations import platform_integration, Platform

log = logging.getLogger("Translator")

class PlatformIntegrationsDialog(QDialog):
    """Dialog for managing platform integrations"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🔗 Platform Integrations")
        self.setModal(True)
        self.resize(800, 650)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        
        # Header
        header = QLabel("🔗 Platform Integrations")
        header.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: 700;
                color: #82c8ff;
                padding: 15px;
            }
        """)
        layout.addWidget(header)
        
        # Description
        desc = QLabel(
            "Enable integrations for Discord, Zoom, Teams, and other platforms.\n"
            "Voice duplication and text translation support for meetings and gaming."
        )
        desc.setStyleSheet("font-size: 13px; color: #9aa0a6; padding: 0 15px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        # Platforms list
        platforms_group = QGroupBox("📱 Available Platforms")
        platforms_layout = QVBoxLayout(platforms_group)
        
        self.platform_checkboxes = {}
        platforms_info = platform_integration.get_all_platforms_info()
        
        for platform, info in platforms_info.items():
            platform_widget = self.create_platform_widget(platform, info)
            platforms_layout.addWidget(platform_widget)
        
        layout.addWidget(platforms_group)
        
        # Setup guide
        guide_group = QGroupBox("📚 Setup Guide")
        guide_layout = QVBoxLayout(guide_group)
        
        self.guide_text = QTextEdit()
        self.guide_text.setReadOnly(True)
        self.guide_text.setMaximumHeight(150)
        self.guide_text.setPlaceholderText("Select a platform to see setup instructions...")
        guide_layout.addWidget(self.guide_text)
        
        layout.addWidget(guide_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.setup_virtual_mic_btn = QPushButton("🎙️ Setup Virtual Microphone")
        self.setup_virtual_mic_btn.clicked.connect(self.setup_virtual_microphone)
        self.setup_virtual_mic_btn.setStyleSheet("""
            QPushButton {
                background: #1a73e8;
                color: white;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: 600;
            }
        """)
        button_layout.addWidget(self.setup_virtual_mic_btn)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        close_btn.setMinimumWidth(120)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
    
    def create_platform_widget(self, platform: Platform, info: dict) -> QWidget:
        """Create a widget for a single platform"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Checkbox
        checkbox = QCheckBox(info['name'])
        checkbox.setChecked(info['enabled'])
        checkbox.setStyleSheet("font-size: 14px; font-weight: 600;")
        checkbox.stateChanged.connect(
            lambda state, p=platform: self.on_platform_toggled(p, state == Qt.CheckState.Checked.value)
        )
        self.platform_checkboxes[platform] = checkbox
        layout.addWidget(checkbox)
        
        # Features
        features = []
        if info['supports_voice']:
            features.append("🎙️ Voice")
        if info['supports_text']:
            features.append("💬 Text")
        
        features_label = QLabel(" | ".join(features))
        features_label.setStyleSheet("font-size: 12px; color: #9aa0a6;")
        layout.addWidget(features_label)
        
        layout.addStretch()
        
        # Info button
        info_btn = QPushButton("ℹ️ Setup")
        info_btn.clicked.connect(lambda: self.show_platform_info(platform))
        info_btn.setMaximumWidth(100)
        layout.addWidget(info_btn)
        
        # Style the widget
        widget.setStyleSheet("""
            QWidget {
                background: rgba(130, 200, 255, 0.05);
                border-radius: 8px;
                padding: 5px;
            }
            QWidget:hover {
                background: rgba(130, 200, 255, 0.1);
            }
        """)
        
        return widget
    
    def on_platform_toggled(self, platform: Platform, enabled: bool):
        """Handle platform enable/disable"""
        if enabled:
            platform_integration.enable_platform(platform)
            log.info(f"Enabled {platform.value}")
        else:
            platform_integration.disable_platform(platform)
            log.info(f"Disabled {platform.value}")
    
    def show_platform_info(self, platform: Platform):
        """Show setup instructions for a platform"""
        instructions = platform_integration.get_setup_instructions(platform)
        self.guide_text.setPlainText(instructions)
    
    def setup_virtual_microphone(self):
        """Show virtual microphone setup guide"""
        if platform_integration.setup_virtual_microphone():
            QMessageBox.information(
                self,
                "Virtual Microphone Setup",
                "Virtual microphone setup initiated.\n\n"
                "Please follow the instructions in your system to complete the setup.\n"
                "After setup, you can use the virtual microphone in your meeting applications."
            )
        else:
            QMessageBox.warning(
                self,
                "Setup Failed",
                "Failed to setup virtual microphone.\n"
                "Please check the logs for more information."
            )
