import sys
import math
import random
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QTextEdit, QPushButton, QHBoxLayout
from PyQt5.QtCore import QTimer, Qt, QPoint, QRect, QSize, pyqtSignal
from PyQt5.QtGui import QPainter, QPen, QColor, QFont

class SiriVoiceWidget(QWidget):
    state_changed = pyqtSignal(str)

    def __init__(self, jarvis_callback=None):
        super().__init__()
        # States: 'listening', 'processing', 'speaking'
        self.current_state = 'listening'
        self.time_offset = 0
        self.wave_amplitude = 0
        self.target_amplitude = 0
        self.jarvis_callback = jarvis_callback
        self.expanded = False
        self.chat_history = []
        self.initUI()
        self.setup_timer()
        self.update_target_amplitude()

        self.state_changed.connect(self._update_state)

    def _update_state(self, state):
        self.set_state(state)

    def initUI(self):
        # Small compact size similar to Siri
        self.setFixedSize(160, 100)

        # Move to top-right corner of the screen
        screen = QApplication.primaryScreen().geometry()
        x = screen.width() - self.width() - 20
        y = 20
        self.move(x, y)

        # Transparent, always on top, frameless
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint |
            Qt.FramelessWindowHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setWindowTitle('JARVIS Assistant')

    def setup_timer(self):
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_animation)
        self.timer.start(30)  # ~33 FPS

    def set_state(self, state):
        self.current_state = state
        self.update_target_amplitude()

    def update_target_amplitude(self):
        if self.current_state == 'listening':
            self.target_amplitude = 15
        elif self.current_state == 'processing':
            self.target_amplitude = 8
        elif self.current_state == 'speaking':
            self.target_amplitude = 25

    def update_animation(self):
        self.time_offset += 0.15
        amp_diff = self.target_amplitude - self.wave_amplitude
        self.wave_amplitude += amp_diff * 0.1
        self.update()

    def get_state_color(self):
        if self.current_state == 'listening':
            return QColor(80, 255, 120, 200)    # Green
        elif self.current_state == 'processing':
            return QColor(255, 80, 80, 200)    # Red
        elif self.current_state == 'speaking':
            return QColor(80, 150, 255, 200)   # Blue

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        center_x, center_y = w // 2, h // 2

        # Background is invisible → only waves are drawn
        self.draw_siri_waveform(painter, center_x, center_y)

    def draw_siri_waveform(self, painter, center_x, center_y):
        state_color = self.get_state_color()
        if self.current_state == 'listening':
            self.draw_listening_wave(painter, center_x, center_y, state_color)
        elif self.current_state == 'processing':
            self.draw_thinking_pattern(painter, center_x, center_y, state_color)
        elif self.current_state == 'speaking':
            self.draw_speaking_wave(painter, center_x, center_y, state_color)
            
    def draw_listening_wave(self, painter, center_x, center_y, color):
        pen = QPen(color, 2.5)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        
        wave_width = 60
        points = []
        
        for x in range(-wave_width//2, wave_width//2, 2):
            y = self.wave_amplitude * math.sin(x * 0.1 + self.time_offset) * \
                math.exp(-abs(x) * 0.015)
            noise = 2 * math.sin(self.time_offset * 2 + x * 0.2)
            y += noise
            points.append(QPoint(center_x + x, int(center_y + y)))
            
        for i in range(len(points) - 1):
            painter.drawLine(points[i], points[i + 1])
            
    def draw_thinking_pattern(self, painter, center_x, center_y, color):
        pen = QPen(color, 3)
        painter.setPen(pen)
        for i in range(3):
            pulse = abs(math.sin(self.time_offset + i * 0.8)) * self.wave_amplitude * 0.3
            x = center_x + (i - 1) * 15
            y = center_y + pulse - 5
            painter.drawEllipse(int(x - 2), int(y - 2), 4, 4)

    def show(self):
        super().show()

    def hide(self):
        super().hide()

    def close(self):
        super().close()
            
    def draw_speaking_wave(self, painter, center_x, center_y, color):
        pen = QPen(color, 2.5)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        
        wave_width = 70
        points = []
        
        for x in range(-wave_width//2, wave_width//2, 2):
            y1 = self.wave_amplitude * 0.6 * math.sin(x * 0.08 + self.time_offset)
            y2 = self.wave_amplitude * 0.3 * math.sin(x * 0.15 + self.time_offset * 1.5)
            y3 = self.wave_amplitude * 0.2 * math.sin(x * 0.3 + self.time_offset * 2)
            y = (y1 + y2 + y3) * math.exp(-abs(x) * 0.01)
            if random.random() > 0.7:
                y += random.uniform(-3, 3)
            points.append(QPoint(center_x + x, int(center_y + y)))
            
        for i in range(len(points) - 1):
            painter.drawLine(points[i], points[i + 1])
            
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.toggle_expanded()
        elif event.button() == Qt.RightButton:
            self.close()
            
    def toggle_expanded(self):
        screen = QApplication.primaryScreen().geometry()
        if not self.expanded:
            # Expand to cover 30% of the right side
            new_width = int(screen.width() * 0.3)
            new_height = int(screen.height() * 0.7)
            self.setFixedSize(new_width, new_height)
            
            # Move to right side
            x = screen.width() - new_width
            y = (screen.height() - new_height) // 2
            self.move(x, y)
            
            # Create chat interface
            self.create_chat_interface()
            self.expanded = True
        else:
            # Return to compact mode
            self.setFixedSize(160, 100)
            x = screen.width() - self.width() - 20
            y = 20
            self.move(x, y)
            
            # Remove chat interface
            for child in self.findChildren(QWidget):
                child.deleteLater()
            self.expanded = False
            
    def create_chat_interface(self):
        # Create a layout for the expanded view
        layout = QVBoxLayout(self)
        
        # Chat history display
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setStyleSheet("""
            QTextEdit {
                background-color: rgba(30, 30, 30, 220);
                color: white;
                border: 1px solid #444;
                border-radius: 10px;
                padding: 10px;
            }
        """)
        layout.addWidget(self.chat_display)
        
        # Input area
        input_layout = QHBoxLayout()
        
        self.input_field = QTextEdit()
        self.input_field.setMaximumHeight(60)
        self.input_field.setPlaceholderText("Type your message here...")
        self.input_field.setStyleSheet("""
            QTextEdit {
                background-color: rgba(50, 50, 50, 220);
                color: white;
                border: 1px solid #444;
                border-radius: 10px;
                padding: 10px;
            }
        """)
        input_layout.addWidget(self.input_field)
        
        send_button = QPushButton("Send")
        send_button.setFixedSize(60, 60)
        send_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        send_button.clicked.connect(self.send_message)
        input_layout.addWidget(send_button)
        
        layout.addLayout(input_layout)
        self.setLayout(layout)
        
        # Load chat history
        self.update_chat_display()
        
    def send_message(self):
        message = self.input_field.toPlainText().strip()
        if message:
            self.add_message("You", message)
            self.input_field.clear()
            
            # Process the message through JARVIS
            if self.jarvis_callback:
                self.set_state('think')
                response = self.jarvis_callback(message)
                self.add_message("JARVIS", response)
                self.set_state('listen')
                
    def add_message(self, sender, message):
        self.chat_history.append({"sender": sender, "message": message})
        self.update_chat_display()
        
    def update_chat_display(self):
        self.chat_display.clear()
        for msg in self.chat_history:
            if msg["sender"] == "You":
                self.chat_display.append(f"<b>You:</b> {msg['message']}")
            else:
                self.chat_display.append(f"<b style='color:#4CAF50'>JARVIS:</b> {msg['message']}")
            self.chat_display.append("")  # Empty line for spacing
        
        # Scroll to bottom
        self.chat_display.verticalScrollBar().setValue(
            self.chat_display.verticalScrollBar().maximum()
        )
        
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            if self.expanded:
                self.toggle_expanded()
            else:
                self.close()
        elif event.key() == Qt.Key_Return and self.expanded:
            if self.input_field.hasFocus():
                self.send_message()