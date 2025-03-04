"""
Основное окно приложения ShogunOSC.
Собирает и координирует работу всех компонентов интерфейса,
обрабатывает сигналы между компонентами.
"""

import asyncio
import logging
import threading
from datetime import datetime

from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                           QLabel, QPushButton, QTextEdit, QGroupBox, QGridLayout,
                           QLineEdit, QSpinBox, QComboBox, QStatusBar, QCheckBox, QSplitter,
                           QAction, QMenu, QToolBar, QApplication)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QTextCursor, QIcon

from gui.status_panel import StatusPanel
from gui.log_panel import LogPanel
from shogun.shogun_client import ShogunWorker
from osc.osc_server import OSCServer, format_osc_message
from logger.custom_logger import add_text_widget_handler
from styles.app_styles import get_palette, get_stylesheet, set_status_style
import config

class ShogunOSCApp(QMainWindow):
    """Главное окно приложения. Отвечает за организацию 
    интерфейса и координацию работы всех компонентов."""
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger('ShogunOSC')
        
        # Инициализация рабочих потоков
        self.shogun_worker = ShogunWorker()
        self.osc_server = None  # Будет создан после настройки интерфейса
        
        # Настройка интерфейса
        self.init_ui()
        
        # Подключение сигналов
        self.connect_signals()
        
        # Запуск рабочих потоков
        self.shogun_worker.start()
        
        # Проверка импорта библиотек
        if not config.IMPORT_SUCCESS:
            self.logger.critical(f"Ошибка импорта библиотек: {config.IMPORT_ERROR}")
            self.log_panel.log_text.append(f'<span style="color:red;font-weight:bold;">ОШИБКА ИМПОРТА БИБЛИОТЕК: {config.IMPORT_ERROR}</span>')
            self.log_panel.log_text.append('<span style="color:red;">Убедитесь, что установлены необходимые библиотеки:</span>')
            self.log_panel.log_text.append('<span style="color:blue;">pip install vicon-core-api shogun-live-api python-osc psutil PyQt5</span>')
    
    def init_ui(self):
        """Инициализация пользовательского интерфейса"""
        self.setWindowTitle("Shogun OSC GUI")
        self.setMinimumSize(800, 600)
        
        # Создаем панель статуса первой, до применения темы
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Готов к работе")
        
        # Теперь можно применять тему
        self.apply_theme(config.DARK_MODE)
        
        # Создаем меню и тулбар
        self.create_menu()
        
        # Основные виджеты
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        
        # Создаем компоненты интерфейса
        self.status_panel = StatusPanel(self.shogun_worker)
        self.log_panel = LogPanel()
        
        # Добавляем панель логов в систему логирования
        add_text_widget_handler(self.log_panel.log_text)
        
        # Добавляем компоненты в основной лейаут
        main_layout.addWidget(self.status_panel)
        main_layout.addWidget(self.log_panel, 1)  # 1 - коэффициент растяжения
        
        # Устанавливаем центральный виджет
        self.setCentralWidget(central_widget)
        
        # Запускаем OSC сервер
        if self.status_panel.osc_panel.osc_enabled.isChecked():
            self.start_osc_server()
    
    def create_menu(self):
        """Создание меню и панели инструментов"""
        # Главное меню
        menubar = self.menuBar()
        
        # Меню "Файл"
        file_menu = menubar.addMenu("Файл")
        
        exit_action = QAction("Выход", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Меню "Настройки"
        settings_menu = menubar.addMenu("Настройки")
        
        self.theme_action = QAction("Тёмная тема", self)
        self.theme_action.setCheckable(True)
        self.theme_action.setChecked(config.DARK_MODE)
        self.theme_action.triggered.connect(self.toggle_theme)
        settings_menu.addAction(self.theme_action)
        
        # Меню "Справка"
        help_menu = menubar.addMenu("Справка")
        
        about_action = QAction("О программе", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
        # Панель инструментов
        toolbar = QToolBar("Основная панель")
        self.addToolBar(toolbar)
        
        # Кнопки для удобного доступа к функциям
        theme_tool_action = QAction("Сменить тему", self)
        theme_tool_action.triggered.connect(self.toggle_theme)
        toolbar.addAction(theme_tool_action)
        
        toolbar.addSeparator()
        
        # Можно добавить другие полезные кнопки на панель инструментов
    
    def connect_signals(self):
        """Подключение сигналов между компонентами"""
        # Сигналы от панели состояния
        self.status_panel.osc_panel.osc_enabled.stateChanged.connect(self.toggle_osc_server)
    
    def toggle_osc_server(self, state):
        """Включение/выключение OSC-сервера"""
        if state == Qt.Checked:
            self.start_osc_server()
        else:
            self.stop_osc_server()
    
    def start_osc_server(self):
        """Запуск OSC-сервера"""
        ip = self.status_panel.osc_panel.ip_input.text()
        port = self.status_panel.osc_panel.port_input.value()
        
        # Останавливаем предыдущий сервер, если был
        self.stop_osc_server()
        
        # Создаем и запускаем новый сервер
        self.osc_server = OSCServer(ip, port, self.shogun_worker)
        self.osc_server.message_signal.connect(self.log_panel.add_osc_message)
        self.osc_server.start()
        
        # Блокируем изменение настроек при запущенном сервере
        self.status_panel.osc_panel.ip_input.setEnabled(False)
        self.status_panel.osc_panel.port_input.setEnabled(False)
        
        self.logger.info(f"OSC-сервер запущен на {ip}:{port}")
    
    def stop_osc_server(self):
        """Остановка OSC-сервера"""
        if self.osc_server and self.osc_server.isRunning():
            self.osc_server.stop()
            self.osc_server.wait()  # Ждем завершения потока
            self.osc_server = None
            
            # Разблокируем настройки
            self.status_panel.osc_panel.ip_input.setEnabled(True)
            self.status_panel.osc_panel.port_input.setEnabled(True)
            
            self.logger.info("OSC-сервер остановлен")
    
    def apply_theme(self, dark_mode=False):
        """Применяет выбранную тему ко всему приложению"""
        # Обновляем настройку темной темы в конфигурации
        config.DARK_MODE = dark_mode
        config.app_settings['dark_mode'] = dark_mode
        config.save_settings(config.app_settings)
        
        # Применяем палитру и стили
        palette = get_palette(dark_mode)
        stylesheet = get_stylesheet(dark_mode)
        
        # Устанавливаем палитру и стилевую таблицу для приложения
        app = QApplication.instance()
        app.setPalette(palette)
        app.setStyleSheet(stylesheet)
        
        # Уведомляем пользователя о смене темы
        theme_name = "тёмная" if dark_mode else "светлая"
        self.status_bar.showMessage(f"Применена {theme_name} тема", 3000)
        
        # Обновляем состояние чекбокса в меню
        if hasattr(self, 'theme_action'):
            self.theme_action.setChecked(dark_mode)
    
    def toggle_theme(self):
        """Переключение между светлой и тёмной темой"""
        self.apply_theme(not config.DARK_MODE)
    
    def show_about(self):
        """Отображает окно 'О программе'"""
        about_text = (
            "<h2>Shogun OSC GUI</h2>"
            "<p>Приложение для управления Shogun Live через OSC-протокол</p>"
            "<p>Версия: 1.0</p>"
            "<p>Лицензия: MIT</p>"
        )
        
        # Можно использовать QMessageBox для отображения, 
        # но для простоты просто добавим в лог
        self.logger.info("О программе: Shogun OSC GUI v1.0")
        self.log_panel.log_text.append(about_text)
    
    def closeEvent(self, event):
        """Обработка закрытия приложения"""
        # Сохраняем настройки
        config.app_settings["osc_ip"] = self.status_panel.osc_panel.ip_input.text()
        config.app_settings["osc_port"] = self.status_panel.osc_panel.port_input.value()
        config.app_settings["osc_enabled"] = self.status_panel.osc_panel.osc_enabled.isChecked()
        config.save_settings(config.app_settings)
        
        # Останавливаем рабочие потоки
        if self.shogun_worker:
            self.shogun_worker.stop()
            self.shogun_worker.wait()
        
        self.stop_osc_server()
        
        self.logger.info("Приложение закрыто")
        event.accept()