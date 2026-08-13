# project/project_manager.py
import os
import json
import random
import copy
from PyQt5.QtGui import QColor

class Project:
    def __init__(self, project_file_path=None, images_dir=None):
        # Поддержка обеих сигнатур:
        # 1. Project(project_file_path, images_dir=None)  - новый формат
        # 2. Project(images_dir, annotations_file)         - старый формат (обратная совместимость)
        if images_dir is not None and isinstance(project_file_path, str) and isinstance(images_dir, str):
            if os.path.isdir(project_file_path) or images_dir.endswith(('.json', '.vf')):
                # Передано (images_dir, annotations_file)
                self.file_path = images_dir
                self.images_dir = project_file_path
            else:
                self.file_path = project_file_path
                self.images_dir = images_dir
        else:
            self.file_path = project_file_path
            self.images_dir = images_dir

        # Данные проекта внутри единого файла
        self.version = "2.1.0"
        self.classes = ["unknown"]
        self.class_colors = {}
        self.class_hierarchy = ["unknown"]
        self.last_image = None
        self.images_data = {}  # Структура: filename -> {"main": [...], "auto": [...]}

        # Списки для работы интерфейса
        self.images_list = []
        self.image_types = {}  # Кэш классов для фильтрации в UI

    @property
    def annotations_file(self):
        """Алиас для обратной совместимости."""
        return self.file_path

    @annotations_file.setter
    def annotations_file(self, path):
        self.file_path = path

    @property
    def annotations(self):
        """Обратная совместимость: возвращает словарь с main-аннотациями."""
        return {img: data.get("main", []) for img, data in self.images_data.items()}

    @annotations.setter
    def annotations(self, value):
        """Обратная совместимость: установка словаря аннотаций."""
        if not isinstance(value, dict):
            return
        for img, boxes in value.items():
            if img not in self.images_data:
                self.images_data[img] = {"main": [], "auto": []}
            if isinstance(boxes, list):
                self.images_data[img]["main"] = self._normalize_boxes(boxes)
            elif isinstance(boxes, dict) and ("main" in boxes or "auto" in boxes):
                self.images_data[img] = {
                    "main": self._normalize_boxes(boxes.get("main", [])),
                    "auto": self._normalize_boxes(boxes.get("auto", []))
                }
        self.build_image_types_cache()

    def _normalize_boxes(self, boxes):
        """Нормализует формат боксов в список словарей."""
        if not isinstance(boxes, list):
            return []
        norm = []
        for box in boxes:
            if isinstance(box, dict):
                norm.append(box)
        return norm

    def _validate_data(self, data):
        """Проверяет корректность структуры данных проекта."""
        if not isinstance(data, dict):
            return False
        if "annotations" in data and not isinstance(data["annotations"], dict):
            return False
        if "images" in data and not isinstance(data["images"], dict):
            return False
        if "class_colors" in data and not isinstance(data["class_colors"], dict):
            return False
        if "class_hierarchy" in data and not isinstance(data["class_hierarchy"], list):
            return False
        if "classes" in data and not isinstance(data["classes"], list):
            return False
        return True

    def load(self):
        """Загружает файл проекта (.vf или legacy .json) и сканирует привязанную папку с картинками."""
        if self.file_path and os.path.exists(self.file_path):
            with open(self.file_path, 'r', encoding='utf-8') as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError as e:
                    raise ValueError(f"Не удалось прочесть файл проекта: {e}")

            if not self._validate_data(data):
                raise ValueError("Некорректная структура данных файла проекта.")

            # Восстанавливаем сохраненный путь к картинкам
            if not self.images_dir:
                self.images_dir = data.get("images_dir")

            if not self.images_dir:
                self.images_dir = os.path.dirname(self.file_path)

            # Формат 1: Монолитный .vf проект (содержит ключ 'images')
            if "images" in data and isinstance(data["images"], dict):
                self.images_data = {}
                for img, val in data["images"].items():
                    if isinstance(val, dict):
                        self.images_data[img] = {
                            "main": self._normalize_boxes(val.get("main", [])),
                            "auto": self._normalize_boxes(val.get("auto", []))
                        }
                    elif isinstance(val, list):
                        self.images_data[img] = {"main": self._normalize_boxes(val), "auto": []}
            # Формат 2: Формат с ключом 'annotations'
            elif "annotations" in data and isinstance(data["annotations"], dict):
                self.images_data = {}
                for img, boxes in data["annotations"].items():
                    self.images_data[img] = {"main": self._normalize_boxes(boxes), "auto": []}
            # Формат 3: Плоский словарь {filename: [boxes]}
            else:
                self.images_data = {}
                for k, v in data.items():
                    if isinstance(v, list):
                        self.images_data[k] = {"main": self._normalize_boxes(v), "auto": []}

            self.classes = data.get("classes", [])
            self.class_colors = data.get("class_colors", {})
            self.class_hierarchy = data.get("class_hierarchy", [])
            self.last_image = data.get("last_image")
        else:
            # Инициализация для нового файла
            if not self.images_dir and self.file_path:
                self.images_dir = os.path.dirname(self.file_path)
            self.images_data = {}
            self.classes = []
            self.class_hierarchy = []

        # Нормализуем путь к папке с изображениями
        if self.images_dir:
            self.images_dir = os.path.normpath(self.images_dir)

        # Сканируем изображения, если папка существует
        if self.images_dir and os.path.exists(self.images_dir) and os.path.isdir(self.images_dir):
            self.images_list = [f for f in os.listdir(self.images_dir)
                                if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp'))]
            self.images_list.sort()
        elif not self.images_list and self.images_data:
            self.images_list = sorted(list(self.images_data.keys()))

        # Гарантируем наличие слотов разметки для каждого найденного файла
        for img in self.images_list:
            if img not in self.images_data:
                self.images_data[img] = {"main": [], "auto": []}
            else:
                if "main" not in self.images_data[img]: self.images_data[img]["main"] = []
                if "auto" not in self.images_data[img]: self.images_data[img]["auto"] = []

        # Извлекаем все уникальные классы из аннотаций, если список классов пуст
        all_annotation_classes = set()
        for modes in self.images_data.values():
            for box in modes.get("main", []) + modes.get("auto", []):
                cls_name = box.get("class")
                if cls_name:
                    all_annotation_classes.add(cls_name)

        if not self.classes:
            if all_annotation_classes:
                self.classes = sorted(all_annotation_classes)
            else:
                self.classes = ["unknown"]
        else:
            for cls in all_annotation_classes:
                if cls not in self.classes:
                    self.classes.append(cls)
            self.classes.sort()

        if not self.class_hierarchy:
            self.class_hierarchy = copy.deepcopy(self.classes)
        else:
            for cls in self.classes:
                self._add_missing_to_hierarchy(cls)

        self.generate_class_colors()
        self.clean_class_colors()
        self.build_image_types_cache()

    def save(self):
        """Сохраняет состояние проекта в файл .vf."""
        if not self.file_path:
            return
        data = {
            "project_version": self.version,
            "images_dir": self.images_dir,
            "classes": self.classes,
            "class_colors": self.class_colors,
            "class_hierarchy": self.class_hierarchy,
            "last_image": self.last_image,
            "images": self.images_data
        }
        os.makedirs(os.path.dirname(os.path.abspath(self.file_path)), exist_ok=True)
        with open(self.file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def build_image_types_cache(self):
        """Создает кэш тегов классов для фильтрации в главном окне."""
        self.image_types = {}
        for img in self.images_list:
            types = set()
            if img in self.images_data:
                for box in self.images_data[img].get("main", []):
                    types.add(box.get("class", "unknown"))
                for box in self.images_data[img].get("auto", []):
                    types.add(box.get("class", "unknown"))
            self.image_types[img] = types

    def get_annotations(self, filename, mode='main'):
        """Универсальный геттер: mode может быть 'main' или 'auto'."""
        if filename in self.images_data:
            return self.images_data[filename].get(mode, [])
        return []

    def set_annotations(self, filename, boxes, mode='main'):
        """Универсальный сеттер разметки."""
        if filename not in self.images_data:
            self.images_data[filename] = {"main": [], "auto": []}

        norm_boxes = self._normalize_boxes(boxes)
        self.images_data[filename][mode] = norm_boxes

        for box in norm_boxes:
            cls = box.get("class", "unknown")
            if cls not in self.classes:
                self.classes.append(cls)
                self.classes.sort()
                self._add_missing_to_hierarchy(cls)

        self.generate_class_colors()
        self.build_image_types_cache()

    def approve_auto_annotations(self, filename):
        """Переносит авторазметку модели в основную для выбранного кадра."""
        if filename in self.images_data:
            auto_boxes = self.images_data[filename].get("auto", [])
            self.images_data[filename]["main"] = copy.deepcopy(auto_boxes)
            self.images_data[filename]["auto"] = []
            self.build_image_types_cache()

    def delete_image(self, filename):
        """Удаляет изображение из проекта."""
        if filename in self.images_list:
            self.images_list.remove(filename)
        if filename in self.images_data:
            del self.images_data[filename]
        if filename in self.image_types:
            del self.image_types[filename]

    def rename_class(self, old_name, new_name):
        """Переименовывает класс во всех аннотациях, иерархии и цветах."""
        if old_name == new_name or not old_name:
            return

        # Обновляем аннотации во всех изображениях и ветках
        for img_data in self.images_data.values():
            for mode in ("main", "auto"):
                for box in img_data.get(mode, []):
                    if box.get("class") == old_name:
                        box["class"] = new_name

        # Обновляем список классов
        if old_name in self.classes:
            self.classes.remove(old_name)
        if new_name not in self.classes:
            self.classes.append(new_name)
        self.classes.sort()

        # Обновляем цвета
        if old_name in self.class_colors:
            color = self.class_colors.pop(old_name)
            self.class_colors[new_name] = color
        else:
            self.generate_class_colors()

        # Обновляем иерархию
        def _rename_in_hierarchy(items):
            for i, item in enumerate(items):
                if isinstance(item, str):
                    if item == old_name:
                        items[i] = new_name
                elif isinstance(item, dict) and "name" in item:
                    if item["name"] == old_name:
                        item["name"] = new_name
                    if "children" in item:
                        _rename_in_hierarchy(item["children"])

        _rename_in_hierarchy(self.class_hierarchy)
        self.clean_class_colors()
        self.build_image_types_cache()

    def delete_class(self, class_name):
        """Удаляет класс из проекта и очищает аннотации с этим классом."""
        if not class_name:
            return

        # Удаляем боксы с этим классом
        for img_data in self.images_data.values():
            for mode in ("main", "auto"):
                img_data[mode] = [b for b in img_data.get(mode, []) if b.get("class") != class_name]

        if class_name in self.classes:
            self.classes.remove(class_name)
        if not self.classes:
            self.classes = ["unknown"]

        if class_name in self.class_colors:
            del self.class_colors[class_name]

        def _delete_from_hierarchy(items):
            new_items = []
            for item in items:
                if isinstance(item, str):
                    if item != class_name:
                        new_items.append(item)
                elif isinstance(item, dict) and "name" in item:
                    if item["name"] != class_name:
                        if "children" in item:
                            item["children"] = _delete_from_hierarchy(item["children"])
                        new_items.append(item)
            return new_items

        self.class_hierarchy = _delete_from_hierarchy(self.class_hierarchy)
        if not self.class_hierarchy:
            self.class_hierarchy = copy.deepcopy(self.classes)

        self.generate_class_colors()
        self.clean_class_colors()
        self.build_image_types_cache()

    def generate_class_colors(self):
        """Генерирует цвета для всех классов, у которых ещё нет цвета."""
        for cls in self.classes:
            if cls not in self.class_colors:
                hue = random.randint(0, 359)
                self.class_colors[cls] = QColor.fromHsv(hue, 255, 255).name()

    def clean_class_colors(self):
        """Удаляет цвета для классов, которых больше нет в self.classes."""
        current_classes = set(self.classes)
        for cls in list(self.class_colors.keys()):
            if cls not in current_classes:
                del self.class_colors[cls]

    def _flatten_hierarchy(self, items, result):
        for item in items:
            if isinstance(item, str):
                result.add(item)
            elif isinstance(item, dict) and "name" in item:
                result.add(item["name"])
                if "children" in item:
                    self._flatten_hierarchy(item["children"], result)

    def update_classes_from_hierarchy(self):
        classes_set = set()
        self._flatten_hierarchy(self.class_hierarchy, classes_set)
        self.classes = sorted(classes_set)
        if not self.classes:
            self.classes = ["unknown"]
        self.generate_class_colors()
        self.clean_class_colors()

    def _add_missing_to_hierarchy(self, class_name):
        existing = set()
        self._flatten_hierarchy(self.class_hierarchy, existing)
        if class_name not in existing:
            self.class_hierarchy.append(class_name)