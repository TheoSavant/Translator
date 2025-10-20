"""Resizable overlay window for displaying translations"""
import time
import logging
from enum import Enum
from collections import deque
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from config import config

log = logging.getLogger("Translator")

class ResizableOverlay(QWidget):
    """Fully resizable overlay with corner and edge dragging + Netflix/Google Live Captions-style scrolling"""
    
    CORNER_SIZE = 20
    EDGE_SIZE = 10
    MIN_WIDTH = 200
    MIN_HEIGHT = 80
    
    class ResizeMode(Enum):
        NONE = 0
        MOVE = 1
        TOP_LEFT = 2
        TOP_RIGHT = 3
        BOTTOM_LEFT = 4
        BOTTOM_RIGHT = 5
        TOP = 6
        BOTTOM = 7
        LEFT = 8
        RIGHT = 9
    
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)
        
        # Resize state
        self.resize_mode = self.ResizeMode.NONE
        self.drag_start_pos = None
        self.drag_start_geometry = None
        
        # Container with glassmorphic effect
        self.container = QWidget(self)
        self.container.setObjectName("overlayContainer")
        
        # Main content
        # Use a scrolling label for Google Live Captions effect
        self.label_container = QWidget(self.container)
        self.label_container.setMouseTracking(True)
        
        self.label = QLabel("", self.label_container)
        self.label.setWordWrap(True)
        self.label.setAlignment(Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignLeft)
        self.label.setMouseTracking(True)
        self.label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        label_layout = QVBoxLayout(self.label_container)
        label_layout.addStretch()
        label_layout.addWidget(self.label)
        label_layout.setContentsMargins(0, 0, 0, 0)
        label_layout.setSpacing(0)
        
        # Resize indicators (corner dots) - Material Design 3 style
        self.corner_indicators = []
        for _ in range(4):
            indicator = QLabel("", self.container)
            indicator.setFixedSize(10, 10)
            indicator.setStyleSheet("""
                background: qradialgradient(cx:0.5, cy:0.5, radius:0.5,
                    fx:0.5, fy:0.5, stop:0 rgba(130, 200, 255, 0.9), stop:1 rgba(100, 181, 246, 0.7));
                border-radius: 5px;
                border: 1px solid rgba(255,255,255,0.3);
            """)
            indicator.hide()
            self.corner_indicators.append(indicator)
        
        layout = QVBoxLayout(self.container)
        layout.addWidget(self.label_container)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(0)
        
        main = QVBoxLayout(self)
        main.addWidget(self.container)
        main.setContentsMargins(0, 0, 0, 0)
        
        # Live captions style: show last N words with smooth scrolling
        self.text_buffer = deque(maxlen=config.get("max_words", 100))
        max_lines = config.get("subtitle_lines", 3)
        self.displayed_lines = deque(maxlen=max_lines)  # Show last N lines like Google Live Captions
        self.current_sentence = []  # Build current sentence
        self.last_update_time = time.time()
        self.live_captions_mode = config.get("live_captions_mode", True)
        self.subtitle_update_delay = config.get("subtitle_update_delay", 10) / 1000.0  # Convert ms to seconds
        
        # Professional fade animation for Netflix-style smooth text transitions
        self.fade_effect = QGraphicsOpacityEffect(self.label)
        self.label.setGraphicsEffect(self.fade_effect)
        
        self.fade_animation = QPropertyAnimation(self.fade_effect, b"opacity")
        self.fade_animation.setDuration(250)
        self.fade_animation.setStartValue(0.0)
        self.fade_animation.setEndValue(1.0)
        self.fade_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        # Add slide animation for Netflix-style entrance
        self.slide_animation = QPropertyAnimation(self.label, b"pos")
        self.slide_animation.setDuration(250)
        self.slide_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        self.apply_style()
        geom = config.get("overlay_position", [100, 100, 800, 180])
        # Ensure geometry is valid
        geom = self._validate_geometry(geom)
        self.setGeometry(*geom)
        self.setVisible(config.get("overlay_visible", True))
    
    def _validate_geometry(self, geom):
        """Validate and fix geometry to avoid Windows constraints errors"""
        x, y, w, h = geom
        
        # Ensure minimum size
        w = max(w, self.MIN_WIDTH)
        h = max(h, self.MIN_HEIGHT)
        
        # Ensure position is on screen
        screen = QApplication.primaryScreen().geometry()
        x = max(0, min(x, screen.width() - w))
        y = max(0, min(y, screen.height() - h))
        
        return [x, y, w, h]
        
        # Update corner positions
        self._update_corner_positions()
    
    def apply_style(self):
        """Netflix/Google-level glassmorphic professional styling"""
        fs = config.get("font_size", 22)
        tc = config.get("text_color", "#FFFFFF")
        bg = config.get("bg_color", "rgba(15,15,20,0.92)")
        
        # Professional Material Design 3 styling
        self.setStyleSheet(f"""
            #overlayContainer {{
                background: {bg};
                border-radius: 20px;
                border: 1.5px solid rgba(255,255,255,0.15);
                backdrop-filter: blur(20px);
                box-shadow: 0 8px 32px rgba(0,0,0,0.4);
            }}
            QLabel {{
                color: {tc};
                font-size: {fs}px;
                font-weight: 500;
                line-height: 1.7;
                background: transparent;
                font-family: "Segoe UI", "SF Pro Display", -apple-system, system-ui, sans-serif;
                letter-spacing: 0.3px;
                text-shadow: 0 2px 8px rgba(0,0,0,0.3);
            }}
        """)
    
    def _update_corner_positions(self):
        """Update visual corner indicators"""
        w, h = self.width(), self.height()
        positions = [
            (5, 5),  # Top-left
            (w - 13, 5),  # Top-right
            (5, h - 13),  # Bottom-left
            (w - 13, h - 13)  # Bottom-right
        ]
        for indicator, pos in zip(self.corner_indicators, positions):
            indicator.move(*pos)
    
    def add_text(self, text, is_translation=True):
        """Add text with Google Live Captions-style smooth scrolling and instant updates"""
        if not text.strip():
            return
        
        if not self.live_captions_mode:
            # Legacy mode: just add to buffer
            for word in text.split():
                self.text_buffer.append(word)
            self.update_display_legacy()
            return
        
        # Google Live Captions mode: instant word-by-word updates
        words = text.split()
        
        # Add words one at a time for smooth appearance (if delay is small enough)
        if self.subtitle_update_delay < 0.020:  # Less than 20ms
            # Ultra-fast mode: add all words at once
            self.current_sentence.extend(words)
            self.update_display_smooth()
        else:
            # Smooth mode: add words with slight delay for visual effect
            for word in words:
                self.current_sentence.append(word)
                self.update_display_smooth()
                QApplication.processEvents()  # Allow UI to update
        
        # Check if we should create a new line (sentence break detection)
        sentence_text = " ".join(self.current_sentence)
        should_new_line = (
            len(self.current_sentence) > 12 or  # Wrap sooner for readability
            any(sentence_text.rstrip().endswith(punct) for punct in ['.', '!', '?', '。', '！', '？', ',', ';'])
        )
        
        if should_new_line and len(self.current_sentence) > 0:
            # Move current sentence to displayed lines with smooth transition
            self.displayed_lines.append(sentence_text)
            self.current_sentence = []
            self.update_display_smooth()
    
    def update_display_legacy(self):
        """Legacy update mode (simple buffer display)"""
        if not self.text_buffer:
            self.label.setText("")
            return
        text = " ".join(list(self.text_buffer))
        self.label.setText(text)
    
    def update_display_smooth(self):
        """Update display with Netflix/Google Live Captions-style smooth transitions - optimized for speed"""
        if not self.displayed_lines and not self.current_sentence:
            self.label.setText("")
            return
        
        # Build display text: show last N completed lines + current building sentence
        max_lines = config.get("subtitle_lines", 3)
        lines = list(self.displayed_lines)
        if self.current_sentence:
            lines.append(" ".join(self.current_sentence))
        
        # Keep only last N lines for clean display (Netflix/Google Live Captions style)
        display_text = "\n".join(lines[-max_lines:])
        
        # Update with configurable throttling for live effect
        current_time = time.time()
        time_since_last = current_time - self.last_update_time
        
        # Use configurable delay (default 10ms = 100 FPS for very responsive updates)
        if time_since_last > self.subtitle_update_delay:
            self.label.setText(display_text)
            # Netflix-style subtle fade for new content (only on longer pauses)
            if self.fade_animation.state() != QPropertyAnimation.State.Running and time_since_last > 0.4:
                self.fade_animation.setStartValue(0.88)
                self.fade_animation.setEndValue(1.0)
                self.fade_animation.setDuration(150)
                self.fade_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
                self.fade_animation.start()
            self.last_update_time = current_time
        else:
            # For very rapid updates, just update text without animation for maximum speed
            self.label.setText(display_text)
    
    def clear_subtitles(self):
        """Clear all subtitle text"""
        self.text_buffer.clear()
        self.displayed_lines.clear()
        self.current_sentence = []
        self.label.setText("")
    
    def _get_resize_mode(self, pos):
        """Determine resize mode based on cursor position"""
        x, y = pos.x(), pos.y()
        w, h = self.width(), self.height()
        cs, es = self.CORNER_SIZE, self.EDGE_SIZE
        
        # Check corners first (priority)
        if x < cs and y < cs:
            return self.ResizeMode.TOP_LEFT
        elif x > w - cs and y < cs:
            return self.ResizeMode.TOP_RIGHT
        elif x < cs and y > h - cs:
            return self.ResizeMode.BOTTOM_LEFT
        elif x > w - cs and y > h - cs:
            return self.ResizeMode.BOTTOM_RIGHT
        
        # Check edges
        elif y < es:
            return self.ResizeMode.TOP
        elif y > h - es:
            return self.ResizeMode.BOTTOM
        elif x < es:
            return self.ResizeMode.LEFT
        elif x > w - es:
            return self.ResizeMode.RIGHT
        
        # Center = move
        return self.ResizeMode.MOVE
    
    def _update_cursor(self, mode):
        """Update cursor based on resize mode"""
        cursor_map = {
            self.ResizeMode.NONE: Qt.CursorShape.ArrowCursor,
            self.ResizeMode.MOVE: Qt.CursorShape.SizeAllCursor,
            self.ResizeMode.TOP_LEFT: Qt.CursorShape.SizeFDiagCursor,
            self.ResizeMode.BOTTOM_RIGHT: Qt.CursorShape.SizeFDiagCursor,
            self.ResizeMode.TOP_RIGHT: Qt.CursorShape.SizeBDiagCursor,
            self.ResizeMode.BOTTOM_LEFT: Qt.CursorShape.SizeBDiagCursor,
            self.ResizeMode.TOP: Qt.CursorShape.SizeVerCursor,
            self.ResizeMode.BOTTOM: Qt.CursorShape.SizeVerCursor,
            self.ResizeMode.LEFT: Qt.CursorShape.SizeHorCursor,
            self.ResizeMode.RIGHT: Qt.CursorShape.SizeHorCursor,
        }
        self.setCursor(cursor_map.get(mode, Qt.CursorShape.ArrowCursor))
    
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.resize_mode = self._get_resize_mode(e.pos())
            self.drag_start_pos = e.globalPosition().toPoint()
            self.drag_start_geometry = self.geometry()
            
            # Show corner indicators
            for indicator in self.corner_indicators:
                indicator.show()
    
    def mouseMoveEvent(self, e):
        if self.resize_mode == self.ResizeMode.NONE:
            # Update cursor for hover
            mode = self._get_resize_mode(e.pos())
            self._update_cursor(mode)
            return
        
        if not self.drag_start_pos:
            return
        
        delta = e.globalPosition().toPoint() - self.drag_start_pos
        geom = QRect(self.drag_start_geometry)
        
        # Apply resize/move based on mode
        if self.resize_mode == self.ResizeMode.MOVE:
            geom.moveTopLeft(geom.topLeft() + delta)
        
        elif self.resize_mode == self.ResizeMode.TOP_LEFT:
            geom.setTopLeft(geom.topLeft() + delta)
        elif self.resize_mode == self.ResizeMode.TOP_RIGHT:
            geom.setTopRight(geom.topRight() + delta)
        elif self.resize_mode == self.ResizeMode.BOTTOM_LEFT:
            geom.setBottomLeft(geom.bottomLeft() + delta)
        elif self.resize_mode == self.ResizeMode.BOTTOM_RIGHT:
            geom.setBottomRight(geom.bottomRight() + delta)
        
        elif self.resize_mode == self.ResizeMode.TOP:
            geom.setTop(geom.top() + delta.y())
        elif self.resize_mode == self.ResizeMode.BOTTOM:
            geom.setBottom(geom.bottom() + delta.y())
        elif self.resize_mode == self.ResizeMode.LEFT:
            geom.setLeft(geom.left() + delta.x())
        elif self.resize_mode == self.ResizeMode.RIGHT:
            geom.setRight(geom.right() + delta.x())
        
        # Enforce minimum size with more flexible constraints
        min_w = max(self.MIN_WIDTH, 135)
        min_h = max(self.MIN_HEIGHT, 57)
        
        if geom.width() < min_w:
            if self.resize_mode in [self.ResizeMode.LEFT, self.ResizeMode.TOP_LEFT, self.ResizeMode.BOTTOM_LEFT]:
                geom.setLeft(geom.right() - min_w)
            else:
                geom.setWidth(min_w)
        
        if geom.height() < min_h:
            if self.resize_mode in [self.ResizeMode.TOP, self.ResizeMode.TOP_LEFT, self.ResizeMode.TOP_RIGHT]:
                geom.setTop(geom.bottom() - min_h)
            else:
                geom.setHeight(min_h)
        
        # Validate geometry before setting to avoid Windows errors
        if geom.width() >= self.MIN_WIDTH and geom.height() >= self.MIN_HEIGHT:
            try:
                self.setGeometry(geom)
            except Exception as e:
                log.debug(f"Geometry set failed: {e}")
                # Fall back to current geometry if setting fails
                pass
        self._update_corner_positions()
    
    def mouseReleaseEvent(self, e):
        if self.resize_mode != self.ResizeMode.NONE:
            geom = self.geometry()
            # Validate and save geometry
            validated_geom = self._validate_geometry([geom.x(), geom.y(), geom.width(), geom.height()])
            config.set("overlay_position", validated_geom)
            
            # Hide corner indicators
            for indicator in self.corner_indicators:
                indicator.hide()
        
        self.resize_mode = self.ResizeMode.NONE
        self.drag_start_pos = None
        self.drag_start_geometry = None
        self.setCursor(Qt.CursorShape.ArrowCursor)
    
    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.container.setGeometry(0, 0, self.width(), self.height())
        self._update_corner_positions()
    
    def enterEvent(self, e):
        # Show corner indicators on hover
        for indicator in self.corner_indicators:
            indicator.show()
    
    def leaveEvent(self, e):
        # Hide corner indicators when not hovering
        if self.resize_mode == self.ResizeMode.NONE:
            for indicator in self.corner_indicators:
                indicator.hide()

