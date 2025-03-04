#!/usr/bin/env python3
"""
Точка входа в приложение ShogunOSC GUI.
Запускает основное окно и инициализирует необходимые компоненты.
"""

import sys
import traceback
import logging
from PyQt5.QtWidgets import QApplication, QMessageBox

from logger.custom_logger import setup_logging
import config

def show_error_message(message, details=None):
    """Показывает диалоговое окно с ошибкой"""
    error_dialog = QMessageBox()
    error_dialog.setIcon(QMessageBox.Critical)
    error_dialog.setWindowTitle("Ошибка")
    error_dialog.setText(message)
    if details:
        error_dialog.setDetailedText(details)
    error_dialog.setStandardButtons(QMessageBox.Ok)
    error_dialog.exec_()

def main():
    """Основная функция запуска приложения"""
    try:
        # Настройка логирования
        setup_logging()
        logger = logging.getLogger('ShogunOSC')
        
        # Проверяем успешность импорта библиотек в config
        if not config.IMPORT_SUCCESS:
            error_msg = f"Ошибка импорта библиотек: {config.IMPORT_ERROR}"
            logger.critical(error_msg)
            print(error_msg)
            print("Убедитесь, что установлены необходимые библиотеки:")
            print("pip install vicon-core-api shogun-live-api python-osc psutil PyQt5")
            
            # Создаем приложение только для показа ошибки
            app = QApplication(sys.argv)
            show_error_message(
                "Ошибка импорта необходимых библиотек", 
                f"Ошибка: {config.IMPORT_ERROR}\n\n"
                "Убедитесь, что установлены необходимые библиотеки:\n"
                "pip install vicon-core-api shogun-live-api python-osc psutil PyQt5"
            )
            return
        
        # Импортируем GUI только после проверки зависимостей
        from gui.main_window import ShogunOSCApp
        
        # Создаем приложение
        app = QApplication(sys.argv)
        app.setStyle('Fusion')
        
        # Создаем и показываем главное окно
        window = ShogunOSCApp()
        
        # Применяем тему при запуске если нужно
        if config.DARK_MODE:
            from styles.app_styles import get_palette, get_stylesheet
            app.setPalette(get_palette(True))
            app.setStyleSheet(get_stylesheet(True))
        
        window.show()
        
        # Запускаем главный цикл приложения
        sys.exit(app.exec_())
        
    except Exception as e:
        # Получаем полный стек ошибки
        error_details = traceback.format_exc()
        error_message = f"Ошибка при запуске приложения: {str(e)}"
        
        # Логируем ошибку если логгер уже настроен
        try:
            logger = logging.getLogger('ShogunOSC')
            logger.critical(error_message)
            logger.critical(error_details)
        except:
            # Если логгер еще не настроен, выводим в консоль
            print(error_message)
            print(error_details)
        
        # Создаем приложение только для показа ошибки
        app = QApplication(sys.argv)
        show_error_message(error_message, error_details)
        sys.exit(1)

if __name__ == "__main__":
    main()