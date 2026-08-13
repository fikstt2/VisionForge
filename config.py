# config.py
import os
import sys
import json

def get_base_dir():
    """Возвращает базовую директорию для хранения данных."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.getcwd()

BASE_DIR = get_base_dir()
CONFIG_FILE = os.path.join(BASE_DIR, "settings.json")
VERSION = "2.0.0"

DEFAULT_CONFIG = {
    "detector_path": "",
    "classifier_path": "",
    "cls_conf": 0.5,
    "thumbnail_cache": True,
    "thumbnail_quality": 70,
    "async_image_loading": False,
    "auto_hide_panel": False,
    "theme": "Тёмная",
    "language": "ru",
    "recent_projects": [],  # список словарей: {json_path, name, thumbnail, description}
}

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                user_config = json.load(f)
                return {**DEFAULT_CONFIG, **user_config}
        except Exception as e:
            print(f"Warning: Failed to parse {CONFIG_FILE} ({e}). Generating default config.")
            backup_file = CONFIG_FILE + ".bak"
            try:
                if os.path.exists(backup_file):
                    os.remove(backup_file)
                os.rename(CONFIG_FILE, backup_file)
            except Exception:
                pass
            return DEFAULT_CONFIG.copy()
    return DEFAULT_CONFIG.copy()

def save_config(config_dict):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config_dict, f, indent=4, ensure_ascii=False)

def ensure_directories():
    os.makedirs(os.path.join(BASE_DIR, "data"), exist_ok=True)
    os.makedirs(os.path.join(BASE_DIR, "models"), exist_ok=True)

def get_recent_projects():
    """Возвращает список недавних проектов в виде словарей."""
    raw = load_config().get("recent_projects", [])
    result = []
    for p in raw:
        if isinstance(p, str):
            # Старый формат — конвертируем в словарь
            base_name = os.path.splitext(os.path.basename(p))[0]
            if not base_name or base_name == "project":
                base_name = os.path.basename(os.path.dirname(p)) or "Project"
            result.append({
                "json_path": p,
                "name": base_name,
                "thumbnail": "",
                "description": "",
            })
        elif isinstance(p, dict):
            result.append(p)
    return result

def add_recent_project(project_file_path, project=None):
    """
    Добавляет проект в список недавних.
    Поддерживает:
      - project_file_path: строка пути к .vf/.json
      - project_file_path: словарь {"json_path": ..., "name": ..., ...}
      - project_file_path: экземпляр Project
    project — объект Project (опционально); если передан, берётся превью из первого изображения.
    """
    cfg = load_config()
    recent = cfg.get("recent_projects", [])

    thumbnail_path = ""
    description = ""
    name = ""

    # Если первым аргументом передан словарь
    if isinstance(project_file_path, dict):
        dict_data = project_file_path
        path_str = dict_data.get("json_path", "")
        name = dict_data.get("name", "")
        thumbnail_path = dict_data.get("thumbnail", "")
        description = dict_data.get("description", "")
        project_file_path = path_str
    # Если передан объект Project напрямую первым аргументом
    elif hasattr(project_file_path, "file_path"):
        project = project_file_path
        project_file_path = getattr(project, "file_path", "")

    if not project_file_path or not isinstance(project_file_path, str):
        return

    # Нормализуем путь
    project_file_path = os.path.normpath(project_file_path)

    # Удаляем старую запись с таким же путём (в любом формате)
    recent = [p for p in recent if (
        (isinstance(p, str) and os.path.normpath(p) != project_file_path) or
        (isinstance(p, dict) and os.path.normpath(p.get("json_path", "")) != project_file_path)
    )]

    # Генерируем превью: берём первое изображение из папки проекта
    if not thumbnail_path and project is not None:
        images_dir = getattr(project, "images_dir", "")
        images_list = getattr(project, "images_list", [])
        if images_dir and images_list:
            first_img = os.path.join(images_dir, images_list[0])
            if os.path.exists(first_img):
                thumbnail_path = first_img

    # Если project не передан, пробуем найти превью из сохранённого .vf файла
    if not thumbnail_path and os.path.exists(project_file_path):
        try:
            with open(project_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            images_dir = data.get("images_dir", "")
            images = list(data.get("images", {}).keys())
            if images_dir and images:
                first_img = os.path.join(images_dir, images[0])
                if os.path.exists(first_img):
                    thumbnail_path = first_img
        except Exception:
            pass

    if not name:
        name = (
            getattr(project, "name", None)
            or os.path.splitext(os.path.basename(project_file_path))[0]
            or "Project"
        )

    entry = {
        "json_path": project_file_path,
        "name": name,
        "thumbnail": thumbnail_path,
        "description": description,
    }

    recent.insert(0, entry)
    cfg["recent_projects"] = recent[:15]
    save_config(cfg)

def update_recent_project_thumbnail(json_path, thumbnail_path):
    """Обновляет путь к превью у существующего проекта в списке недавних."""
    cfg = load_config()
    recent = cfg.get("recent_projects", [])
    json_path = os.path.normpath(json_path)
    for p in recent:
        if isinstance(p, dict) and os.path.normpath(p.get("json_path", "")) == json_path:
            p["thumbnail"] = thumbnail_path
            break
    cfg["recent_projects"] = recent
    save_config(cfg)

def update_recent_project_description(json_path, description):
    """Обновляет описание у существующего проекта в списке недавних."""
    cfg = load_config()
    recent = cfg.get("recent_projects", [])
    json_path = os.path.normpath(json_path)
    found = False
    for p in recent:
        if isinstance(p, dict) and os.path.normpath(p.get("json_path", "")) == json_path:
            p["description"] = description
            found = True
            break
    if not found:
        # Добавляем запись, если её нет
        recent.insert(0, {
            "json_path": json_path,
            "name": os.path.splitext(os.path.basename(json_path))[0],
            "thumbnail": "",
            "description": description,
        })
    cfg["recent_projects"] = recent
    save_config(cfg)