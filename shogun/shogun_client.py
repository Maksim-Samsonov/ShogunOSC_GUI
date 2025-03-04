"""
Модуль для взаимодействия с Shogun Live API.
Предоставляет функциональность подключения, мониторинга и управления записью.
"""

import asyncio
import logging
import time
import psutil
from PyQt5.QtCore import QThread, pyqtSignal

from vicon_core_api import Client
from shogun_live_api import CaptureServices
import config

class ShogunWorker(QThread):
    """Рабочий поток для взаимодействия с Shogun Live"""
    connection_signal = pyqtSignal(bool)  # Сигнал состояния подключения
    status_signal = pyqtSignal(str)       # Сигнал статуса
    recording_signal = pyqtSignal(bool)   # Сигнал состояния записи
    take_name_signal = pyqtSignal(str)    # Сигнал названия текущего тейка
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger('ShogunOSC')
        self.running = True
        self.connected = False
        self.shogun_client = None
        self.capture = None
        self.shogun_pid = None
        self.loop = None
        
    def run(self):
        """Основной метод потока"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        # Первая попытка подключения
        self.connected = self.loop.run_until_complete(self.connect_shogun())
        self.connection_signal.emit(self.connected)
        
        # Основной цикл мониторинга
        while self.running:
            # Проверяем наличие процесса Shogun Live
            shogun_running = self.check_shogun_process()
            
            # Проверяем соединение, если процесс запущен
            if shogun_running:
                if not self.connected:
                    self.logger.info("Shogun Live обнаружен. Выполняем подключение...")
                    self.connected = self.loop.run_until_complete(self.connect_shogun())
                    self.connection_signal.emit(self.connected)
                else:
                    # Проверяем существующее соединение
                    connection_ok = self.loop.run_until_complete(self.ensure_connection())
                    if not connection_ok:
                        self.logger.warning("Соединение с Shogun Live потеряно")
                        self.connected = False
                        self.connection_signal.emit(False)
                    
                    # Если подключены, обновляем статус записи
                    if self.connected:
                        is_recording = self.loop.run_until_complete(self.check_shogun())
                        self.recording_signal.emit(is_recording)
                        
                        # Обновляем имя тейка, если есть доступ к capture
                        try:
                            if self.capture:
                                name = self.capture.latest_capture_name()
                                # Проверяем тип данных и преобразуем в строку, если это кортеж
                                if isinstance(name, tuple):
                                    name_str = str(name[0]) if name and len(name) > 0 else "Нет активного тейка"
                                else:
                                    name_str = str(name) if name else "Нет активного тейка"
                                
                                self.take_name_signal.emit(name_str)
                        except Exception as e:
                            self.logger.debug(f"Ошибка получения имени тейка: {e}")
            else:
                if self.connected:
                    self.logger.warning("Shogun Live не обнаружен. Соединение потеряно.")
                    self.connected = False
                    self.connection_signal.emit(False)
                    self.recording_signal.emit(False)
                    self.take_name_signal.emit("Нет соединения")
            
            # Обновляем статус в интерфейсе
            status = config.STATUS_CONNECTED if self.connected else config.STATUS_DISCONNECTED
            self.status_signal.emit(status)
            
            # Короткая пауза перед следующей проверкой
            time.sleep(1)
    
    def check_shogun_process(self):
        """Проверяет, запущен ли процесс Shogun Live и изменился ли его PID"""
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                proc_name = proc.info['name']
                if proc_name and ('ShogunLive' in proc_name or 'Shogun Live' in proc_name):
                    pid = proc.info['pid']
                    # Если PID изменился, считаем что Shogun перезапущен
                    if self.shogun_pid and self.shogun_pid != pid:
                        self.logger.info(f"Обнаружен перезапуск Shogun Live (PID: {self.shogun_pid} -> {pid})")
                        self.shogun_pid = pid
                        self.connected = False  # Сбрасываем подключение
                        return True
                    self.shogun_pid = pid
                    return True
            return False
        except Exception as e:
            self.logger.debug(f"Ошибка проверки процесса Shogun: {e}")
            return False
    
    async def connect_shogun(self):
        """Подключение к Shogun Live"""
        try:
            self.logger.info("Подключение к Shogun Live...")
            self.shogun_client = Client('localhost')
            self.capture = CaptureServices(self.shogun_client)
            self.logger.info("Подключено к Shogun Live")
            return True
        except Exception as e:
            self.logger.error(f"Ошибка подключения к Shogun Live: {e}")
            return False
    
    async def ensure_connection(self):
        """Проверка соединения и переподключение при необходимости"""
        if not self.shogun_client or not self.capture:
            return await self.connect_shogun()
        
        try:
            # Простая проверка - пытаемся выполнить запрос к API
            status = str(self.capture.latest_capture_state())
            return True
        except Exception as e:
            self.logger.debug(f"Ошибка проверки соединения: {e}")
            return await self.reconnect_shogun()
    
    async def reconnect_shogun(self):
        """Переподключение к Shogun Live"""
        self.logger.info("Попытка переподключения к Shogun Live...")
        
        # Закрываем существующее соединение если оно есть
        if self.shogun_client:
            try:
                # Закрытие клиентского соединения если есть такой метод
                if hasattr(self.shogun_client, 'disconnect'):
                    self.shogun_client.disconnect()
                elif hasattr(self.shogun_client, 'close'):
                    self.shogun_client.close()
            except Exception as e:
                self.logger.debug(f"Ошибка при закрытии соединения: {e}")
        
        # Пытаемся переподключиться с экспоненциальной отсрочкой
        attempt = 0
        max_attempts = config.MAX_RECONNECT_ATTEMPTS
        base_delay = config.BASE_RECONNECT_DELAY
        
        while attempt < max_attempts:
            result = await self.connect_shogun()
            if result:
                self.recording_signal.emit(await self.check_shogun())
                return True
            
            attempt += 1
            # Экспоненциальная отсрочка с максимальным значением
            delay = min(base_delay * (1.5 ** (attempt - 1)), config.MAX_RECONNECT_DELAY)
            self.logger.debug(f"Попытка {attempt} не удалась. Следующая через {delay:.1f} секунд...")
            
            await asyncio.sleep(delay)
        
        self.logger.error(f"Не удалось переподключиться к Shogun Live после {max_attempts} попыток")
        return False
    
    async def check_shogun(self):
        """Проверка состояния записи"""
        try:
            if not self.capture:
                return False
                
            status = str(self.capture.latest_capture_state())
            is_recording = 'Started' in status
            return is_recording
        except Exception as e:
            self.logger.debug(f"Ошибка проверки состояния Shogun Live: {e}")
            return False
    
    async def startcapture(self):
        """Запуск записи"""
        try:
            # Проверяем соединение перед операцией
            if not await self.ensure_connection():
                self.logger.error("Не удалось установить соединение с Shogun Live")
                return None
                
            self.capture.start_capture()
            self.logger.info("Запись начата в Shogun Live")
            
            # Получаем и возвращаем имя записи
            capture_name = self.capture.latest_capture_name()
            
            # Обрабатываем случай, когда возвращается кортеж
            if isinstance(capture_name, tuple):
                name_str = str(capture_name[0]) if capture_name and len(capture_name) > 0 else "Активная запись"
            else:
                name_str = str(capture_name) if capture_name else "Активная запись"
                
            self.take_name_signal.emit(name_str)
            return capture_name
        except Exception as e:
            self.logger.error(f"Ошибка запуска записи: {e}")
            # Пробуем переподключиться и повторить операцию
            if await self.reconnect_shogun():
                try:
                    self.capture.start_capture()
                    self.logger.info("Запись начата в Shogun Live после переподключения")
                    
                    capture_name = self.capture.latest_capture_name()
                    
                    # Обрабатываем случай, когда возвращается кортеж
                    if isinstance(capture_name, tuple):
                        name_str = str(capture_name[0]) if capture_name and len(capture_name) > 0 else "Активная запись"
                    else:
                        name_str = str(capture_name) if capture_name else "Активная запись"
                    
                    self.take_name_signal.emit(name_str)
                    return capture_name
                except Exception as e2:
                    self.logger.error(f"Не удалось запустить запись после переподключения: {e2}")
            return None
    
    async def stopcapture(self):
        """Остановка записи"""
        try:
            # Проверяем соединение перед операцией
            if not await self.ensure_connection():
                self.logger.error("Не удалось установить соединение с Shogun Live")
                return False
                
            self.capture.stop_capture(0)
            self.logger.info("Запись остановлена в Shogun Live")
            self.take_name_signal.emit("Нет активной записи")
            return True
        except Exception as e:
            self.logger.error(f"Ошибка остановки записи: {e}")
            # Пробуем переподключиться и повторить операцию
            if await self.reconnect_shogun():
                try:
                    self.capture.stop_capture(0)
                    self.logger.info("Запись остановлена в Shogun Live после переподключения")
                    self.take_name_signal.emit("Нет активной записи")
                    return True
                except Exception as e2:
                    self.logger.error(f"Не удалось остановить запись после переподключения: {e2}")
            return False
    
    def stop(self):
        """Остановка рабочего потока"""
        self.running = False