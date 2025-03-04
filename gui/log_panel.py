"""
Панель отображения логов и OSC-сообщений.
"""

import logging
from datetime import datetime

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                           QLabel, QPushButton, QTextEdit, QGroupBox, 
                           QSplitter)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QTextCursor

from osc.osc_server import format_osc_message
import config

class LogTextEdit(QTextEdit):
    """Текстовое поле для отображения логов с ограничением строк"""
    def __init__(self, max_lines=1000):
        super().__init__()
        self.max_lines = max_lines
        self.setReadOnly(True)
        self.setLineWrapMode(QTextEdit.NoWrap)
        self.document().setMaximumBlockCount(max_lines)
    
    def append_text(self, text):
        """Добавление текста с проверкой ограничения строк"""
        self.append(text)
        self.moveCursor(QTextCursor.End)

class LogPanel(QWidget):
    """Панель для отображения логов и OSC-сообщений"""
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger('ShogunOSC')
        self.init_ui()
    
    def init_ui(self):
        """Инициализация интерфейса панели логов"""
        main_layout = QVBoxLayout()
        
        # Создаем разделитель для журнала логов и OSC-сообщений
        splitter = QSplitter(Qt.Vertical)
        
        # Панель журнала логов
        log_group = QGroupBox("Журнал событий")
        log_layout = QVBoxLayout()
        
        self.log_text = LogTextEdit(config.LOG_MAX_LINES)
        log_layout.addWidget(self.log_text)
        
        # Кнопки управления логом
        log_buttons_layout = QHBoxLayout()
        
        self.clear_log_button = QPushButton("Очистить лог")
        self.clear_log_button.clicked.connect(self.clear_log)
        log_buttons_layout.addWidget(self.clear_log_button)
        
        self.save_log_button = QPushButton("Сохранить лог")
        self.save_log_button.clicked.connect(self.save_log)
        log_buttons_layout.addWidget(self.save_log_button)
        
        log_layout.addLayout(log_buttons_layout)
        log_group.setLayout(log_layout)
        
        # Панель OSC-сообщений
        osc_messages_group = QGroupBox("Полученные OSC-сообщения")
        osc_messages_layout = QVBoxLayout()
        
        self.osc_messages_text = LogTextEdit(100)  # Меньше строк для сообщений
        osc_messages_layout.addWidget(self.osc_messages_text)
        
        self.clear_messages_button = QPushButton("Очистить сообщения")
        self.clear_messages_button.clicked.connect(self.clear_osc_messages)
        osc_messages_layout.addWidget(self.clear_messages_button)
        
        osc_messages_group.setLayout(osc_messages_layout)
        
        # Добавляем панели в разделитель
        splitter.addWidget(log_group)
        splitter.addWidget(osc_messages_group)
        splitter.setSizes([400, 200])  # Начальные размеры
        
        # Добавляем разделитель в основной лейаут
        main_layout.addWidget(splitter)
        self.setLayout(main_layout)
    
    def clear_log(self):
        """Очистка журнала логов"""
        self.log_text.clear()
        self.logger.info("Журнал логов очищен")
    
    def clear_osc_messages(self):
        """Очистка журнала OSC-сообщений"""
        self.osc_messages_text.clear()
    
    def add_osc_message(self, address, value):
        """Добавление OSC-сообщения в журнал"""
        message = format_osc_message(address, value)
        self.osc_messages_text.append(message)
        self.osc_messages_text.moveCursor(QTextCursor.End)
    
    def save_log(self):
        """Сохранение журнала логов в файл"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"shogun_osc_log_{timestamp}.html"
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("<html><head><meta charset='utf-8'><title>ShogunOSC Log</title></head><body>")
                f.write(self.log_text.toHtml())
                f.write("</body></html>")
            
            self.logger.info(f"Журнал логов сохранен в файл: {filename}")
        except Exception as e:
            self.logger.error(f"Ошибка при сохранении журнала: {e}")