"""
Модуль OSC-сервера для приема и обработки OSC-сообщений.
"""

import asyncio
import logging
import threading
from datetime import datetime
from PyQt5.QtCore import QThread, pyqtSignal

from pythonosc import dispatcher, osc_server
import config

class OSCServer(QThread):
    """Поток OSC-сервера для приема и обработки OSC-сообщений"""
    message_signal = pyqtSignal(str, str)  # Сигнал для полученного OSC-сообщения (адрес, значение)
    
    def __init__(self, ip="0.0.0.0", port=5555, shogun_worker=None):
        super().__init__()
        self.logger = logging.getLogger('ShogunOSC')
        self.ip = ip
        self.port = port
        self.shogun_worker = shogun_worker
        self.running = True
        self.dispatcher = dispatcher.Dispatcher()
        self.server = None
        
        # Настройка обработчиков OSC-сообщений
        self.setup_dispatcher()
        
    def setup_dispatcher(self):
        """Настройка обработчиков OSC-сообщений"""
        self.dispatcher.map(config.OSC_START_RECORDING, self.start_recording)
        self.dispatcher.map(config.OSC_STOP_RECORDING, self.stop_recording)
        self.dispatcher.set_default_handler(self.default_handler)
    
    def start_recording(self, address, *args):
        """Обработчик команды запуска записи"""
        self.logger.info(f"Получена команда OSC: {address} -> Запуск записи")
        self.message_signal.emit(address, "Запуск записи")
        
        if self.shogun_worker and self.shogun_worker.connected:
            threading.Thread(target=self._run_async_task, 
                             args=(self.shogun_worker.startcapture,)).start()
        else:
            self.logger.warning("Не удалось запустить запись: нет подключения к Shogun Live")
    
    def stop_recording(self, address, *args):
        """Обработчик команды остановки записи"""
        self.logger.info(f"Получена команда OSC: {address} -> Остановка записи")
        self.message_signal.emit(address, "Остановка записи")
        
        if self.shogun_worker and self.shogun_worker.connected:
            threading.Thread(target=self._run_async_task, 
                             args=(self.shogun_worker.stopcapture,)).start()
        else:
            self.logger.warning("Не удалось остановить запись: нет подключения к Shogun Live")
    
    def default_handler(self, address, *args):
        """Обработчик для неизвестных OSC-сообщений"""
        args_str = ", ".join(str(arg) for arg in args) if args else "нет аргументов"
        self.logger.debug(f"Получено неизвестное OSC-сообщение: {address} -> {args_str}")
        self.message_signal.emit(address, args_str)
    
    def _run_async_task(self, coro_func):
        """Запускает асинхронную функцию в отдельном цикле событий"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro_func())
        finally:
            loop.close()
    
    def run(self):
        """Запуск OSC-сервера"""
        try:
            self.logger.info(f"Запуск OSC-сервера на {self.ip}:{self.port}")
            self.server = osc_server.ThreadingOSCUDPServer((self.ip, self.port), self.dispatcher)
            
            # Запускаем сервер с возможностью остановки
            while self.running:
                self.server.handle_request()
        except Exception as e:
            self.logger.error(f"Ошибка OSC-сервера: {e}")
    
    def stop(self):
        """Остановка OSC-сервера"""
        self.running = False
        # Закрываем сервер если он создан
        if self.server:
            self.server.server_close()
        self.logger.info("OSC-сервер остановлен")

def format_osc_message(address, value, with_timestamp=True):
    """Форматирует OSC-сообщение для отображения"""
    if with_timestamp:
        timestamp = datetime.now().strftime("%H:%M:%S")
        return f"<b>[{timestamp}]</b> {address} → {value}"
    else:
        return f"{address} → {value}"