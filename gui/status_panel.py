"""
Панель статуса состояния Shogun Live и настроек OSC.
"""

import asyncio
import logging
import threading

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                            QLabel, QPushButton, QGroupBox, QGridLayout,
                            QLineEdit, QSpinBox, QCheckBox)
from PyQt5.QtCore import Qt

import config
from styles.app_styles import set_status_style

class ShogunPanel(QGroupBox):
    """Панель информации о состоянии Shogun Live и кнопок управления"""
    def __init__(self, shogun_worker):
        super().__init__("Shogun Live")
        self.logger = logging.getLogger('ShogunOSC')
        self.shogun_worker = shogun_worker
        self.init_ui()
        self.connect_signals()
    
    def init_ui(self):
        """Инициализация интерфейса панели Shogun"""
        layout = QGridLayout()
        
        # Информация о состоянии
        layout.addWidget(QLabel("Статус:"), 0, 0)
        self.status_label = QLabel(config.STATUS_DISCONNECTED)
        set_status_style(self.status_label, "disconnected")
        layout.addWidget(self.status_label, 0, 1)
        
        layout.addWidget(QLabel("Запись:"), 1, 0)
        self.recording_label = QLabel(config.STATUS_RECORDING_INACTIVE)
        self.recording_label.setStyleSheet("color: gray;")
        layout.addWidget(self.recording_label, 1, 1)
        
        layout.addWidget(QLabel("Текущий тейк:"), 2, 0)
        self.take_label = QLabel("Нет данных")
        layout.addWidget(self.take_label, 2, 1)
        
        # Кнопки управления
        button_layout = QHBoxLayout()
        
        self.connect_button = QPushButton("Подключиться")
        self.connect_button.clicked.connect(self.reconnect_shogun)
        button_layout.addWidget(self.connect_button)
        
        self.start_button = QPushButton("Начать запись")
        self.start_button.clicked.connect(self.start_recording)
        self.start_button.setEnabled(False)
        button_layout.addWidget(self.start_button)
        
        self.stop_button = QPushButton("Остановить запись")
        self.stop_button.clicked.connect(self.stop_recording)
        self.stop_button.setEnabled(False)
        button_layout.addWidget(self.stop_button)
        
        layout.addLayout(button_layout, 3, 0, 1, 2)
        self.setLayout(layout)
    
    def connect_signals(self):
        """Подключение сигналов от Shogun Worker"""
        self.shogun_worker.connection_signal.connect(self.update_connection_status)
        self.shogun_worker.recording_signal.connect(self.update_recording_status)
        self.shogun_worker.take_name_signal.connect(self.update_take_name)
    
    def update_connection_status(self, connected):
        """Обновление отображения статуса подключения"""
        if connected:
            self.status_label.setText(config.STATUS_CONNECTED)
            set_status_style(self.status_label, "connected")
            self.start_button.setEnabled(True)
            self.connect_button.setEnabled(False)
        else:
            self.status_label.setText(config.STATUS_DISCONNECTED)
            set_status_style(self.status_label, "disconnected")
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(False)
            self.connect_button.setEnabled(True)
    
    def update_recording_status(self, is_recording):
        """Обновление отображения статуса записи"""
        if is_recording:
            self.recording_label.setText(config.STATUS_RECORDING_ACTIVE)
            set_status_style(self.recording_label, "recording")
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)
        else:
            self.recording_label.setText(config.STATUS_RECORDING_INACTIVE)
            set_status_style(self.recording_label, "")
            self.start_button.setEnabled(self.shogun_worker.connected)
            self.stop_button.setEnabled(False)
    
    def update_take_name(self, name):
        """Обновление имени текущего тейка"""
        self.take_label.setText(name)
    
    def reconnect_shogun(self):
        """Запуск переподключения к Shogun Live"""
        threading.Thread(target=self._run_reconnect).start()
    
    def _run_reconnect(self):
        """Выполнение переподключения в отдельном потоке"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(self.shogun_worker.reconnect_shogun())
            if result:
                self.logger.info("Переподключение выполнено успешно")
            else:
                self.logger.error("Не удалось переподключиться")
        finally:
            loop.close()
    
    def start_recording(self):
        """Запуск записи"""
        threading.Thread(target=self._run_start_recording).start()
    
    def _run_start_recording(self):
        """Запуск записи в отдельном потоке"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self.shogun_worker.startcapture())
        finally:
            loop.close()
    
    def stop_recording(self):
        """Остановка записи"""
        threading.Thread(target=self._run_stop_recording).start()
    
    def _run_stop_recording(self):
        """Остановка записи в отдельном потоке"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self.shogun_worker.stopcapture())
        finally:
            loop.close()

class OSCPanel(QGroupBox):
    """Панель настроек OSC-сервера"""
    def __init__(self):
        super().__init__("OSC Сервер")
        self.init_ui()
    
    def init_ui(self):
        """Инициализация интерфейса панели OSC"""
        layout = QGridLayout()
        
        layout.addWidget(QLabel("IP:"), 0, 0)
        self.ip_input = QLineEdit(config.DEFAULT_OSC_IP)
        layout.addWidget(self.ip_input, 0, 1)
        
        layout.addWidget(QLabel("Порт:"), 1, 0)
        self.port_input = QSpinBox()
        self.port_input.setRange(1000, 65535)
        self.port_input.setValue(config.DEFAULT_OSC_PORT)
        layout.addWidget(self.port_input, 1, 1)
        
        self.osc_enabled = QCheckBox("Включить OSC-сервер")
        self.osc_enabled.setChecked(config.app_settings.get("osc_enabled", True))
        layout.addWidget(self.osc_enabled, 2, 0, 1, 2)
        
        # Информация о командах OSC
        layout.addWidget(QLabel("Доступные команды:"), 3, 0, 1, 2)
        layout.addWidget(QLabel(f"Старт записи: {config.OSC_START_RECORDING}"), 4, 0, 1, 2)
        layout.addWidget(QLabel(f"Стоп записи: {config.OSC_STOP_RECORDING}"), 5, 0, 1, 2)
        
        self.setLayout(layout)

class StatusPanel(QWidget):
    """Составная панель статуса и настроек"""
    def __init__(self, shogun_worker):
        super().__init__()
        self.init_ui(shogun_worker)
    
    def init_ui(self, shogun_worker):
        """Инициализация составной панели"""
        layout = QHBoxLayout()
        
        # Создаем панели
        self.shogun_panel = ShogunPanel(shogun_worker)
        self.osc_panel = OSCPanel()
        
        # Добавляем панели с разным весом
        layout.addWidget(self.shogun_panel, 3)  # Больший вес для панели Shogun
        layout.addWidget(self.osc_panel, 2)
        
        self.setLayout(layout)