import os
import json

class Project:
    def __init__(self, images_dir, annotations_file):
        self.images_dir = images_dir
        self.annotations_file = annotations_file
        self.images_list = []
        self.annotations = {}      # filename -> list of boxes (with 'class' key)
        self.image_types = {}       # filename -> set of classes
        self.classes = []
        self.class_colors = {}      # class -> QColor name (str)
        self.class_hierarchy = []   # иерархия классов (список, где элементы могут быть строками или словарями с ключами name/children)

    def _normalize_boxes(self, boxes):
        """Приводит список боксов к единому формату с ключом 'class'."""
        normalized = []
        for box in boxes:
            if 'class' in box:
                normalized.append(box)
            elif 'tank_type' in box:
                new_box = box.copy()
                new_box['class'] = new_box.pop('tank_type')
                normalized.append(new_box)
            else:
                new_box = box.copy()
                new_box['class'] = 'unknown'
                normalized.append(new_box)
        return normalized

    def generate_class_colors(self):
        """Генерирует случайные цвета для классов, у которых их нет."""
        import random
        for cls in self.classes:
            if cls not in self.class_colors:
                hue = random.randint(0, 359)
                from PyQt5.QtGui import QColor
                color = QColor.fromHsv(hue, 255, 255)
                self.class_colors[cls] = color.name()

    def clean_class_colors(self):
        """Удаляет цвета для классов, которых больше нет."""
        to_delete = [cls for cls in self.class_colors if cls not in self.classes]
        for cls in to_delete:
            del self.class_colors[cls]

    def _flatten_hierarchy(self, items, result):
        """Рекурсивно собирает все имена классов из иерархии."""
        for item in items:
            if isinstance(item, str):
                result.add(item)
            elif isinstance(item, dict) and "name" in item:
                if "children" in item:
                    self._flatten_hierarchy(item["children"], result)

    def update_classes_from_hierarchy(self):
        """Обновляет self.classes на основе текущей иерархии."""
        classes_set = set()
        self._flatten_hierarchy(self.class_hierarchy, classes_set)
        self.classes = sorted(classes_set)
        if not self.classes:
            self.classes = ["unknown"]

    def load(self):
        self.images_list = [f for f in os.listdir(self.images_dir)
                            if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        self.images_list.sort()

        if os.path.exists(self.annotations_file):
            with open(self.annotations_file, 'r', encoding='utf-8') as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError as e:
                    raise ValueError(f"Невозможно разобрать JSON: {e}")

            if not self._validate_data(data):
                raise ValueError("Файл аннотаций имеет неверную структуру.")

            if isinstance(data, dict) and "annotations" in data:
                self.annotations = data["annotations"]
                self.class_colors = data.get("class_colors", {})
                self.class_hierarchy = data.get("class_hierarchy", [])
            else:
                # старая структура (прямой словарь)
                self.annotations = data
                self.class_colors = {}
                self.class_hierarchy = []
        else:
            self.annotations = {}
            self.class_colors = {}
            self.class_hierarchy = []

        # нормализация: если аннотация не список, оборачиваем
        for img, ann in self.annotations.items():
            if not isinstance(ann, list):
                ann = [ann]
            self.annotations[img] = self._normalize_boxes(ann)

        # округляем координаты
        for img, boxes in self.annotations.items():
            for box in boxes:
                if "bbox" in box:
                    box["bbox"] = [round(coord) for coord in box["bbox"]]

        # построение image_types и классов
        self.image_types = {}
        classes_set = set()
        for img in self.images_list:
            types = set()
            boxes = self.annotations.get(img, [])
            for box in boxes:
                cls = box.get('class', 'unknown')
                types.add(cls)
                classes_set.add(cls)
            self.image_types[img] = types

        # Если иерархия пуста, создаём плоскую из классов
        if not self.class_hierarchy:
            self.class_hierarchy = sorted(classes_set)
        else:
            # Обновляем classes на основе иерархии
            self.update_classes_from_hierarchy()

        self.classes = sorted(classes_set)
        if not self.classes:
            self.classes = ["unknown"]

        self.generate_class_colors()
        self.clean_class_colors()

    def _validate_data(self, data):
        """Проверяет, что data имеет ожидаемую структуру.
        Возвращает True, если структура корректна."""
        if not isinstance(data, dict):
            return False
        # Если есть ключ "annotations", проверяем его тип
        if "annotations" in data:
            if not isinstance(data["annotations"], dict):
                return False
            # Дополнительно можно проверить, что значения - списки
            for ann in data["annotations"].values():
                if not isinstance(ann, list):
                    return False
        # Если ключа "annotations" нет, значит, это старый формат? Тоже ок.
        # Проверяем class_colors, если есть
        if "class_colors" in data and not isinstance(data["class_colors"], dict):
            return False
        # class_hierarchy может быть списком
        if "class_hierarchy" in data and not isinstance(data["class_hierarchy"], list):
            return False
        return True

    def save(self):
        # сохраняем в новом формате с иерархией
        data = {
            "annotations": self.annotations,
            "class_colors": self.class_colors,
            "class_hierarchy": self.class_hierarchy
        }
        with open(self.annotations_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def get_annotations(self, filename):
        return self.annotations.get(filename, [])

    def set_annotations(self, filename, boxes):
        self.annotations[filename] = self._normalize_boxes(boxes)
        types = set(box.get('class', 'unknown') for box in self.annotations[filename])
        self.image_types[filename] = types
        # Обновляем общий список классов из иерархии (иерархия не меняется автоматически)
        all_classes = set()
        for img_types in self.image_types.values():
            all_classes.update(img_types)
        self.classes = sorted(all_classes)
        if not self.classes:
            self.classes = ["unknown"]
        # Добавляем новые классы в иерархию, если их там нет
        self._add_missing_classes_to_hierarchy(all_classes)
        self.generate_class_colors()
        self.clean_class_colors()

    def _add_missing_classes_to_hierarchy(self, classes_set):
        """Добавляет в иерархию классы, которые есть в аннотациях, но отсутствуют в иерархии."""
        existing = set()
        self._flatten_hierarchy(self.class_hierarchy, existing)
        missing = classes_set - existing
        if missing:
            # Добавляем отсутствующие классы как плоские элементы на верхний уровень
            self.class_hierarchy.extend(sorted(missing))