"""
Модуль настройки логирования для приложения.
Включает кастомный форматтер для цветного отображения логов в QTextEdit.
"""

import logging
import queue
import os
import sys
from datetime import datetime
from typing import Optional, Dict, Any

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
        # Ограничиваем количество обрабатываемых записей за один раз
        # для предотвращения блокировки интерфейса
        max_records_per_update = 10
        records_processed = 0
        
        while not self.queue.empty() and records_processed < max_records_per_update:
            try:
                record = self.queue.get_nowait()
                formatted_message = self.format(record)
                self.text_widget.append(formatted_message)
                self.text_widget.moveCursor(QTextCursor.End)
                records_processed += 1
            except queue.Empty:
                break
            except Exception as e:
                # Логируем ошибку в консоль, так как логгер может быть недоступен
                print(f"Ошибка при обновлении логов: {e}", file=sys.stderr)

def setup_logging(log_to_file: bool = False, log_dir: Optional[str] = None) -> logging.Logger:
    """
    Настраивает базовое логирование для приложения
    
    Args:
        log_to_file: Включить логирование в файл
        log_dir: Директория для файлов логов
        
    Returns:
        logging.Logger: Настроенный логгер
    """
    # Настраиваем базовое логирование
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Добавляем обработчик для вывода в консоль
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(config.LOG_FORMAT))
    root_logger.addHandler(console_handler)
    
    # Настройка логирования в файл, если требуется
    if log_to_file:
        try:
            if log_dir is None:
                log_dir = os.path.join(config.CONFIG_DIR, "logs")
            
            # Создаем директорию для логов, если не существует
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
            
            # Создаем файл лога с датой и временем
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = os.path.join(log_dir, f"shogun_osc_{timestamp}.log")
            
            # Добавляем обработчик для записи в файл
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setFormatter(logging.Formatter(config.LOG_FORMAT))
            root_logger.addHandler(file_handler)
            
            # Логируем информацию о начале логирования в файл
            root_logger.info(f"Логирование в файл включено: {log_file}")
        except Exception as e:
            root_logger.error(f"Не удалось настроить логирование в файл: {e}")
    
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
    
    # Возвращаем основной логгер приложения
    return logging.getLogger('ShogunOSC')

def add_text_widget_handler(text_widget) -> QTextEditLogger:
    """
    Добавляет обработчик для вывода логов в текстовый виджет
    
    Args:
        text_widget: Виджет QTextEdit для вывода логов
        
    Returns:
        QTextEditLogger: Созданный обработчик логов
    """
    logger = logging.getLogger('ShogunOSC')
    handler = QTextEditLogger(text_widget)
    handler.setLevel(logging.INFO)
    logger.addHandler(handler)
    return handler

def get_system_info() -> Dict[str, Any]:
    """
    Собирает информацию о системе для диагностики
    
    Returns:
        Dict[str, Any]: Словарь с информацией о системе
    """
    import platform
    
    system_info = {
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "processor": platform.processor(),
        "machine": platform.machine(),
        "app_version": config.APP_VERSION
    }
    
    # Добавляем информацию о PyQt
    try:
        from PyQt5.QtCore import QT_VERSION_STR, PYQT_VERSION_STR
        system_info["qt_version"] = QT_VERSION_STR
        system_info["pyqt_version"] = PYQT_VERSION_STR
    except ImportError:
        system_info["qt_version"] = "unknown"
        system_info["pyqt_version"] = "unknown"
    
    return system_info

def log_system_info(logger: logging.Logger) -> None:
    """
    Логирует информацию о системе
    
    Args:
        logger: Логгер для записи информации
    """
    system_info = get_system_info()
    logger.info("=== Информация о системе ===")
    for key, value in system_info.items():
        logger.info(f"{key}: {value}")
    logger.info("===========================")