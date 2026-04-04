# core/i18n.py
"""
Система интернационализации (i18n) для VisionForge.
Позволяет переключаться между русским и английским языками.
"""
import os
import json
from PyQt5.QtCore import QObject, pyqtSignal

class Translator(QObject):
    languageChanged = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._translations = {}
        self._current_lang = "ru"

    def load_language(self, lang: str):
        """Загружает словарь переводов для указанного языка."""
        self._current_lang = lang
        base_dir = os.path.dirname(os.path.dirname(__file__))
        locale_file = os.path.join(base_dir, "locales", f"{lang}.json")
        if os.path.exists(locale_file):
            with open(locale_file, "r", encoding="utf-8") as f:
                self._translations = json.load(f)
        else:
            self._translations = {}
        self.languageChanged.emit(lang)

    def tr(self, text: str) -> str:
        """Возвращает перевод строки на текущий язык. Если перевод не найден — возвращает исходную строку."""
        return self._translations.get(text, text)

    def current_lang(self) -> str:
        """Возвращает код текущего языка."""
        return self._current_lang

# Singleton instance
_translator = Translator()

def load_language(lang: str):
    _translator.load_language(lang)

def tr(text: str) -> str:
    return _translator.tr(text)

def current_lang() -> str:
    return _translator.current_lang()

def get_translator():
    return _translator
