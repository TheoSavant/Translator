"""RVC Model Manager Dialog for uploading and managing custom TTS models"""
import logging
from pathlib import Path
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from core.rvc_manager import rvc_manager
from core.voice_duplication import voice_duplication

log = logging.getLogger("Translator")

class RVCModelDialog(QDialog):
    """Dialog for managing RVC voice duplication models"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🎙️ RVC Voice Duplication Models")
        self.setModal(True)
        self.resize(900, 700)
        self.setup_ui()
        self.refresh_model_list()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        
        # Header
        header = QLabel("🎙️ Voice Duplication Model Manager")
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
            "Upload and manage RVC models for voice duplication.\n"
            "Support for PTH files, index files, and configuration files."
        )
        desc.setStyleSheet("font-size: 13px; color: #9aa0a6; padding: 0 15px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        # Stats panel
        stats_group = QGroupBox("📊 Statistics")
        stats_layout = QHBoxLayout(stats_group)
        self.stats_label = QLabel()
        self.stats_label.setStyleSheet("font-size: 12px; padding: 10px;")
        stats_layout.addWidget(self.stats_label)
        layout.addWidget(stats_group)
        
        # Models list
        models_group = QGroupBox("📁 Installed Models")
        models_layout = QVBoxLayout(models_group)
        
        # Table for models
        self.models_table = QTableWidget()
        self.models_table.setColumnCount(5)
        self.models_table.setHorizontalHeaderLabels(["Model Name", "PTH File", "Index File", "Config", "Status"])
        self.models_table.horizontalHeader().setStretchLastSection(True)
        self.models_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.models_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.models_table.setAlternatingRowColors(True)
        models_layout.addWidget(self.models_table)
        
        # Buttons for model management
        buttons_layout = QHBoxLayout()
        
        self.add_btn = QPushButton("➕ Add New Model")
        self.add_btn.clicked.connect(self.add_model)
        self.add_btn.setStyleSheet("""
            QPushButton {
                background: #1a73e8;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #1557b0;
            }
        """)
        buttons_layout.addWidget(self.add_btn)
        
        self.activate_btn = QPushButton("✅ Activate Selected")
        self.activate_btn.clicked.connect(self.activate_model)
        self.activate_btn.setStyleSheet("""
            QPushButton {
                background: #34a853;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #2d8e47;
            }
        """)
        buttons_layout.addWidget(self.activate_btn)
        
        self.remove_btn = QPushButton("🗑️ Remove Selected")
        self.remove_btn.clicked.connect(self.remove_model)
        self.remove_btn.setStyleSheet("""
            QPushButton {
                background: #ea4335;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #c5221f;
            }
        """)
        buttons_layout.addWidget(self.remove_btn)
        
        self.refresh_btn = QPushButton("🔄 Refresh")
        self.refresh_btn.clicked.connect(self.refresh_model_list)
        buttons_layout.addWidget(self.refresh_btn)
        
        buttons_layout.addStretch()
        models_layout.addLayout(buttons_layout)
        
        layout.addWidget(models_group)
        
        # Close button
        close_layout = QHBoxLayout()
        close_layout.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        close_btn.setMinimumWidth(120)
        close_layout.addWidget(close_btn)
        layout.addLayout(close_layout)
    
    def refresh_model_list(self):
        """Refresh the list of models"""
        self.models_table.setRowCount(0)
        rvc_manager.load_models()
        
        models = rvc_manager.list_models()
        current_model = rvc_manager.get_current_model()
        
        for model_name in models:
            model_info = rvc_manager.get_model_info(model_name)
            is_valid, status = rvc_manager.validate_model(model_name)
            
            row = self.models_table.rowCount()
            self.models_table.insertRow(row)
            
            # Model name
            name_item = QTableWidgetItem(model_name)
            if model_name == current_model:
                name_item.setForeground(QColor("#34a853"))
                name_item.setFont(QFont("", -1, QFont.Weight.Bold))
            self.models_table.setItem(row, 0, name_item)
            
            # PTH file
            pth_status = "✅" if model_info['pth_file'] else "❌"
            self.models_table.setItem(row, 1, QTableWidgetItem(pth_status))
            
            # Index file
            index_status = "✅" if model_info['index_file'] else "⚠️"
            self.models_table.setItem(row, 2, QTableWidgetItem(index_status))
            
            # Config file
            config_status = "✅" if model_info['config_file'] else "⚠️"
            self.models_table.setItem(row, 3, QTableWidgetItem(config_status))
            
            # Status
            status_item = QTableWidgetItem(status if is_valid else "❌ " + status)
            if model_name == current_model:
                status_item.setText("🟢 ACTIVE - " + status)
            status_item.setForeground(QColor("#34a853" if is_valid else "#ea4335"))
            self.models_table.setItem(row, 4, status_item)
        
        # Update stats
        stats = rvc_manager.get_model_stats()
        self.stats_label.setText(
            f"Total Models: {stats['total_models']} | "
            f"With Index: {stats['models_with_index']} | "
            f"With Config: {stats['models_with_config']} | "
            f"Storage Used: {stats['models_dir_size_mb']} MB"
        )
        
        self.models_table.resizeColumnsToContents()
    
    def add_model(self):
        """Add a new RVC model"""
        dialog = AddModelDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh_model_list()
    
    def activate_model(self):
        """Activate the selected model"""
        selected_rows = self.models_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select a model to activate.")
            return
        
        row = selected_rows[0].row()
        model_name = self.models_table.item(row, 0).text()
        
        if voice_duplication.enable(model_name):
            QMessageBox.information(
                self,
                "Model Activated",
                f"Successfully activated model: {model_name}\n\n"
                "Voice duplication mode is now enabled."
            )
            self.refresh_model_list()
        else:
            QMessageBox.critical(
                self,
                "Activation Failed",
                f"Failed to activate model: {model_name}\n\n"
                "Please check the model files and try again."
            )
    
    def remove_model(self):
        """Remove the selected model"""
        selected_rows = self.models_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select a model to remove.")
            return
        
        row = selected_rows[0].row()
        model_name = self.models_table.item(row, 0).text()
        
        reply = QMessageBox.question(
            self,
            "Confirm Removal",
            f"Are you sure you want to remove model: {model_name}?\n\n"
            "This will delete all associated files.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if rvc_manager.remove_model(model_name):
                QMessageBox.information(self, "Success", f"Model {model_name} removed successfully.")
                self.refresh_model_list()
            else:
                QMessageBox.critical(self, "Error", f"Failed to remove model: {model_name}")


class AddModelDialog(QDialog):
    """Dialog for adding a new RVC model"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add RVC Model")
        self.setModal(True)
        self.resize(600, 400)
        
        self.pth_file = None
        self.index_file = None
        self.config_file = None
        self.other_files = []
        
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Model name
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Model Name:"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Enter a unique name for this model")
        name_layout.addWidget(self.name_edit)
        layout.addLayout(name_layout)
        
        # File selection group
        files_group = QGroupBox("📁 Model Files")
        files_layout = QVBoxLayout(files_group)
        
        # PTH file (required)
        pth_layout = QHBoxLayout()
        pth_layout.addWidget(QLabel("PTH File (Required):"))
        self.pth_label = QLabel("No file selected")
        self.pth_label.setStyleSheet("color: #9aa0a6; font-style: italic;")
        pth_layout.addWidget(self.pth_label, 1)
        pth_btn = QPushButton("Browse...")
        pth_btn.clicked.connect(self.select_pth_file)
        pth_layout.addWidget(pth_btn)
        files_layout.addLayout(pth_layout)
        
        # Index file (optional)
        index_layout = QHBoxLayout()
        index_layout.addWidget(QLabel("Index File (Optional):"))
        self.index_label = QLabel("No file selected")
        self.index_label.setStyleSheet("color: #9aa0a6; font-style: italic;")
        index_layout.addWidget(self.index_label, 1)
        index_btn = QPushButton("Browse...")
        index_btn.clicked.connect(self.select_index_file)
        index_layout.addWidget(index_btn)
        files_layout.addLayout(index_layout)
        
        # Config file (optional)
        config_layout = QHBoxLayout()
        config_layout.addWidget(QLabel("Config File (Optional):"))
        self.config_label = QLabel("No file selected")
        self.config_label.setStyleSheet("color: #9aa0a6; font-style: italic;")
        config_layout.addWidget(self.config_label, 1)
        config_btn = QPushButton("Browse...")
        config_btn.clicked.connect(self.select_config_file)
        config_layout.addWidget(config_btn)
        files_layout.addLayout(config_layout)
        
        layout.addWidget(files_group)
        
        # Info label
        info = QLabel(
            "ℹ️ PTH file is required. Index and config files are optional but recommended for better quality."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #1a73e8; font-size: 12px; padding: 10px;")
        layout.addWidget(info)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        add_btn = QPushButton("Add Model")
        add_btn.clicked.connect(self.add_model)
        add_btn.setStyleSheet("""
            QPushButton {
                background: #1a73e8;
                color: white;
                padding: 8px 20px;
                border-radius: 6px;
                font-weight: 600;
            }
        """)
        button_layout.addWidget(add_btn)
        
        layout.addLayout(button_layout)
    
    def select_pth_file(self):
        file, _ = QFileDialog.getOpenFileName(
            self,
            "Select PTH File",
            "",
            "PyTorch Model Files (*.pth *.pt);;All Files (*.*)"
        )
        if file:
            self.pth_file = file
            self.pth_label.setText(Path(file).name)
            self.pth_label.setStyleSheet("color: #34a853; font-weight: 600;")
    
    def select_index_file(self):
        file, _ = QFileDialog.getOpenFileName(
            self,
            "Select Index File",
            "",
            "Index Files (*.index);;All Files (*.*)"
        )
        if file:
            self.index_file = file
            self.index_label.setText(Path(file).name)
            self.index_label.setStyleSheet("color: #34a853; font-weight: 600;")
    
    def select_config_file(self):
        file, _ = QFileDialog.getOpenFileName(
            self,
            "Select Config File",
            "",
            "Config Files (*.json *.yaml *.yml);;All Files (*.*)"
        )
        if file:
            self.config_file = file
            self.config_label.setText(Path(file).name)
            self.config_label.setStyleSheet("color: #34a853; font-weight: 600;")
    
    def add_model(self):
        """Add the model to the manager"""
        model_name = self.name_edit.text().strip()
        
        if not model_name:
            QMessageBox.warning(self, "Invalid Name", "Please enter a model name.")
            return
        
        if not self.pth_file:
            QMessageBox.warning(self, "Missing File", "PTH file is required.")
            return
        
        # Check if model already exists
        if model_name in rvc_manager.list_models():
            QMessageBox.warning(
                self,
                "Model Exists",
                f"A model with name '{model_name}' already exists.\n"
                "Please choose a different name."
            )
            return
        
        # Prepare files dictionary
        files = {}
        if self.pth_file:
            files['pth'] = self.pth_file
        if self.index_file:
            files['index'] = self.index_file
        if self.config_file:
            files['config'] = self.config_file
        
        # Add model
        if rvc_manager.add_model(model_name, files):
            QMessageBox.information(
                self,
                "Success",
                f"Model '{model_name}' added successfully!\n\n"
                "You can now activate it for voice duplication."
            )
            self.accept()
        else:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to add model '{model_name}'.\n"
                "Please check the files and try again."
            )
