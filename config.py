import os
import sys
import json

def get_base_dir():
    """Возвращает базовую директорию для хранения данных."""
    if getattr(sys, 'frozen', False):
        # Для скомпилированного exe: папка, где лежит exe
        return os.path.dirname(sys.executable)
    else:
        # Для разработки: текущая рабочая директория
        # Можно также использовать os.path.dirname(__file__) если уверены, что config.py в корне
        return os.getcwd()

BASE_DIR = get_base_dir()

CONFIG_FILE = os.path.join(BASE_DIR, "settings.json")

DEFAULT_CONFIG = {
    "detector_path": "",
    "classifier_path": "",
    "cls_conf": 0.5,
    "main_images_dir": os.path.join(BASE_DIR, "data", "screenshots"),
    "main_json": os.path.join(BASE_DIR, "annotations", "main.json"),
    "auto_json": os.path.join(BASE_DIR, "data", "auto_annotations", "auto_annotations.json"),
    "font_path": "C:/Windows/Fonts/arial.ttf",
    "thumbnail_cache": True,
    "thumbnail_quality": 70,
    "async_image_loading": False,
    "auto_hide_panel": False,
}

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            user_config = json.load(f)
            return {**DEFAULT_CONFIG, **user_config}
    else:
        return DEFAULT_CONFIG.copy()

def save_config(config):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4, ensure_ascii=False)

def ensure_directories():
    config = load_config()
    dirs_to_create = [
        os.path.dirname(config["main_json"]),
        os.path.dirname(config["auto_json"]),
        config["main_images_dir"],
        os.path.join(BASE_DIR, "models"),
    ]
    for dir_path in dirs_to_create:
        os.makedirs(dir_path, exist_ok=True)
        print(f"Убедился, что папка существует: {dir_path}")

    if not os.path.exists(CONFIG_FILE):
        save_config(DEFAULT_CONFIG)
        print(f"Создан файл настроек: {CONFIG_FILE}")

_settings = load_config()
ensure_directories()

DETECTOR_PATH = _settings["detector_path"]
CLASSIFIER_PATH = _settings["classifier_path"]
CLS_CONF = _settings["cls_conf"]
SCREENSHOTS_DIR = _settings["main_images_dir"]
MAIN_JSON = _settings["main_json"]
AUTO_JSON = _settings["auto_json"]
FONT_PATH = _settings["font_path"]
THUMBNAIL_CACHE = _settings["thumbnail_cache"]
THUMBNAIL_QUALITY = _settings["thumbnail_quality"]
ASYNC_IMAGE_LOADING = _settings["async_image_loading"]
AUTO_HIDE_PANEL = _settings["auto_hide_panel"]