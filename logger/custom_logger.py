"""
Модуль настройки логирования для приложения.
Включает кастомный форматтер для цветного отображения логов в QTextEdit.
"""

import logging
import queue
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtWidgets import QTextEdit
from PyQt5.QtGui import QTextCursor

import config

class ColoredFormatter(logging.Formatter):
    """Форматтер логов с цветами для отображения в HTML"""
    COLORS = {
        'DEBUG': 'gray',
        'INFO': 'darkgreen',
        'WARNING': 'darkorange',
        'ERROR': 'red',
        'CRITICAL': 'purple',
    }

    def format(self, record):
        log_message = super().format(record)
        color = self.COLORS.get(record.levelname, 'black')
        return f'<span style="color:{color};">{log_message}</span>'

class QTextEditLogger(logging.Handler):
    """Хендлер логов для вывода в QTextEdit с использованием очереди"""
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget
        self.queue = queue.Queue()
        self.setFormatter(ColoredFormatter(config.LOG_FORMAT))
        
        # Создаем таймер для обновления интерфейса
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_logs)
        self.update_timer.start(100)  # Обновление каждые 100 мс
        
    def emit(self, record):
        """Добавляет запись лога в очередь"""
        self.queue.put(record)
        
    def update_logs(self):
        """Обновляет текстовый виджет логами из очереди"""
        while not self.queue.empty():
            record = self.queue.get()
            formatted_message = self.format(record)
            self.text_widget.append(formatted_message)
            self.text_widget.moveCursor(QTextCursor.End)

def setup_logging():
    """Настраивает базовое логирование для приложения"""
    logging.basicConfig(level=logging.INFO, format=config.LOG_FORMAT)
    
    # Настройка логгеров для различных модулей
    loggers = {
        'ShogunOSC': logging.INFO,
        'WebUI': logging.INFO,
        'HyperDeck': logging.INFO,
        'aiohttp': logging.ERROR,
    }
    
    for name, level in loggers.items():
        logger = logging.getLogger(name)
        logger.setLevel(level)
    
    return logging.getLogger('ShogunOSC')

def add_text_widget_handler(text_widget):
    """Добавляет обработчик для вывода логов в текстовый виджет"""
    logger = logging.getLogger('ShogunOSC')
    handler = QTextEditLogger(text_widget)
    handler.setLevel(logging.INFO)
    logger.addHandler(handler)
    return handler