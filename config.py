"""
Файл с конфигурационными параметрами и проверкой зависимостей.
"""

import os
import json
from PyQt5.QtCore import QSettings

# Директория конфигурации
CONFIG_DIR = os.path.expanduser("~/.shogun_osc")
CONFIG_FILE = os.path.join(CONFIG_DIR, "settings.json")

# Настройки приложения по умолчанию
DEFAULT_SETTINGS = {
    "dark_mode": False,
    "osc_ip": "0.0.0.0",
    "osc_port": 5555,
    "osc_enabled": True
}

# Менеджер настроек
settings = QSettings("ShogunOSC", "ShogunOSCApp")

def load_settings():
    """Загрузка настроек приложения"""
    # Создаем каталог конфигурации если не существует
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR)
    
    settings_dict = DEFAULT_SETTINGS.copy()
    
    # Используем QSettings для хранения настроек
    for key in DEFAULT_SETTINGS.keys():
        if settings.contains(key):
            value = settings.value(key)
            # Преобразуем строковые значения 'true'/'false' в булевы
            if isinstance(value, str) and value.lower() in ['true', 'false']:
                value = value.lower() == 'true'
            settings_dict[key] = value
    
    return settings_dict

def save_settings(settings_dict):
    """Сохранение настроек приложения"""
    for key, value in settings_dict.items():
        settings.setValue(key, value)
    settings.sync()

# Загружаем настройки
app_settings = load_settings()

# Флаг темной темы
DARK_MODE = app_settings.get("dark_mode", False)

# Проверка зависимостей
IMPORT_SUCCESS = True
IMPORT_ERROR = ""

try:
    # Библиотеки для Shogun Live
    from vicon_core_api import Client
    from shogun_live_api import CaptureServices
    
    # Библиотеки для OSC
    from pythonosc import dispatcher, osc_server
except ImportError as e:
    IMPORT_SUCCESS = False
    IMPORT_ERROR = str(e)

# Настройки OSC-сервера из параметров приложения
DEFAULT_OSC_IP = app_settings.get("osc_ip", "0.0.0.0")
DEFAULT_OSC_PORT = app_settings.get("osc_port", 5555)

# OSC-адреса для управления Shogun Live
OSC_START_RECORDING = "/RecordStartShogunLive"
OSC_STOP_RECORDING = "/RecordStopShogunLive"

# Настройки логирования
LOG_FORMAT = '%(asctime)s [%(levelname)s] %(message)s'
LOG_MAX_LINES = 1000

# Настройки для проверки соединения с Shogun Live
MAX_RECONNECT_ATTEMPTS = 10
BASE_RECONNECT_DELAY = 1
MAX_RECONNECT_DELAY = 15

# Названия статусов для понятного отображения
STATUS_CONNECTED = "Подключено"
STATUS_DISCONNECTED = "Отключено"
STATUS_RECORDING_ACTIVE = "Активна"
STATUS_RECORDING_INACTIVE = "Не активна"