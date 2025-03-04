"""
Модуль OSC-сервера для приема и обработки OSC-сообщений.
"""

import asyncio
import logging
import threading
import socket
from datetime import datetime
from typing import Callable, Any, Optional
from PyQt5.QtCore import QThread, pyqtSignal

from pythonosc import dispatcher, osc_server
import config

class OSCServer(QThread):
    """Поток OSC-сервера для приема и обработки OSC-сообщений"""
    message_signal = pyqtSignal(str, str)  # Сигнал для полученного OSC-сообщения (адрес, значение)
    
    def __init__(self, ip: str = "0.0.0.0", port: int = 5555, shogun_worker = None):
        super().__init__()
        self.logger = logging.getLogger('ShogunOSC')
        self.ip = ip
        self.port = port
        self.shogun_worker = shogun_worker
        self.running = True
        self.dispatcher = dispatcher.Dispatcher()
        self.server = None
        self._socket = None
        
        # Настройка обработчиков OSC-сообщений
        self.setup_dispatcher()
        
    def setup_dispatcher(self) -> None:
        """Настройка обработчиков OSC-сообщений"""
        self.dispatcher.map(config.OSC_START_RECORDING, self.start_recording)
        self.dispatcher.map(config.OSC_STOP_RECORDING, self.stop_recording)
        self.dispatcher.set_default_handler(self.default_handler)
    
    def start_recording(self, address: str, *args: Any) -> None:
        """
        Обработчик команды запуска записи
        
        Args:
            address: OSC-адрес сообщения
            *args: Аргументы OSC-сообщения
        """
        self.logger.info(f"Получена команда OSC: {address} -> Запуск записи")
        self.message_signal.emit(address, "Запуск записи")
        
        if self.shogun_worker and self.shogun_worker.connected:
            threading.Thread(target=self._run_async_task, 
                             args=(self.shogun_worker.startcapture,)).start()
        else:
            self.logger.warning("Не удалось запустить запись: нет подключения к Shogun Live")
    
    def stop_recording(self, address: str, *args: Any) -> None:
        """
        Обработчик команды остановки записи
        
        Args:
            address: OSC-адрес сообщения
            *args: Аргументы OSC-сообщения
        """
        self.logger.info(f"Получена команда OSC: {address} -> Остановка записи")
        self.message_signal.emit(address, "Остановка записи")
        
        if self.shogun_worker and self.shogun_worker.connected:
            threading.Thread(target=self._run_async_task, 
                             args=(self.shogun_worker.stopcapture,)).start()
        else:
            self.logger.warning("Не удалось остановить запись: нет подключения к Shogun Live")
    
    def default_handler(self, address: str, *args: Any) -> None:
        """
        Обработчик для неизвестных OSC-сообщений
        
        Args:
            address: OSC-адрес сообщения
            *args: Аргументы OSC-сообщения
        """
        args_str = ", ".join(str(arg) for arg in args) if args else "нет аргументов"
        self.logger.debug(f"Получено неизвестное OSC-сообщение: {address} -> {args_str}")
        self.message_signal.emit(address, args_str)
    
    def _run_async_task(self, coro_func: Callable) -> Any:
        """
        Запускает асинхронную функцию в отдельном цикле событий
        
        Args:
            coro_func: Асинхронная функция для выполнения
            
        Returns:
            Any: Результат выполнения функции
        """
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro_func())
        finally:
            loop.close()
    
    def run(self) -> None:
        """Запуск OSC-сервера"""
        try:
            self.logger.info(f"Запуск OSC-сервера на {self.ip}:{self.port}")
            
            # Создаем сервер с обработкой ошибок
            try:
                self.server = osc_server.ThreadingOSCUDPServer((self.ip, self.port), self.dispatcher)
                self._socket = self.server.socket
            except socket.error as e:
                self.logger.error(f"Не удалось создать OSC-сервер: {e}")
                # Сигнализируем об ошибке
                self.message_signal.emit("ERROR", f"Не удалось запустить OSC-сервер: {e}")
                return
            
            # Устанавливаем таймаут для сокета, чтобы можно было корректно остановить сервер
            self._socket.settimeout(0.5)
            
            # Запускаем сервер с возможностью остановки
            while self.running:
                try:
                    self.server.handle_request()
                except socket.timeout:
                    # Таймаут сокета - нормальная ситуация, продолжаем работу
                    continue
                except Exception as e:
                    if self.running:  # Логируем ошибку только если сервер должен работать
                        self.logger.error(f"Ошибка при обработке OSC-запроса: {e}")
        except Exception as e:
            self.logger.error(f"Критическая ошибка OSC-сервера: {e}")
    
    def stop(self) -> None:
        """Остановка OSC-сервера"""
        self.running = False
        # Закрываем сервер если он создан
        if self.server:
            try:
                self.server.server_close()
            except Exception as e:
                self.logger.error(f"Ошибка при закрытии OSC-сервера: {e}")
        self.logger.info("OSC-сервер остановлен")

def format_osc_message(address: str, value: Any, with_timestamp: bool = True) -> str:
    """
    Форматирует OSC-сообщение для отображения
    
    Args:
        address: OSC-адрес сообщения
        value: Значение сообщения
        with_timestamp: Добавлять ли временную метку
        
    Returns:
        str: Отформатированное сообщение
    """
    if with_timestamp:
        timestamp = datetime.now().strftime("%H:%M:%S")
        return f"<b>[{timestamp}]</b> {address} → {value}"
    else:
        return f"{address} → {value}"