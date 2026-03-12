# ui/prepare_dataset_dialog.py
import os
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QDoubleSpinBox, QPushButton, QGroupBox,
                             QRadioButton, QFileDialog, QMessageBox, QProgressDialog,
                             QComboBox, QCheckBox, QAbstractItemView, QLineEdit)
from PyQt5.QtCore import Qt
from ui.theme import get_current_theme_style
from project.dataset_preparer import prepare_detection_dataset, prepare_classification_dataset
from project.project_manager import Project
from ui.class_hierarchy_widget import ClassHierarchyWidget

class PrepareDatasetDialog(QDialog):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.setWindowTitle("Подготовка датасета")
        self.setModal(True)
        self.setMinimumWidth(800)
        self.setMinimumHeight(650)
        self.setStyleSheet(get_current_theme_style())

        layout = QVBoxLayout(self)

        # Тип задачи
        task_group = QGroupBox("Тип задачи")
        task_layout = QHBoxLayout()
        self.task_detection = QRadioButton("Детекция")
        self.task_classification = QRadioButton("Классификация")
        self.task_detection.setChecked(True)
        self.task_detection.toggled.connect(self.on_task_changed)
        task_layout.addWidget(self.task_detection)
        task_layout.addWidget(self.task_classification)
        task_layout.addStretch()
        task_group.setLayout(task_layout)
        layout.addWidget(task_group)

        # Выбор проекта
        source_group = QGroupBox("Исходный проект")
        source_layout = QVBoxLayout()
        self.source_main = QRadioButton("Основной проект")
        self.source_auto = QRadioButton("Авто-проект")
        self.source_other = QRadioButton("Другая папка")
        self.source_main.setChecked(True)
        source_layout.addWidget(self.source_main)
        source_layout.addWidget(self.source_auto)
        source_layout.addWidget(self.source_other)

        self.other_path_edit = QLineEdit()
        self.other_path_edit.setPlaceholderText("Путь к папке с изображениями и annotations.json")
        self.other_path_edit.setEnabled(False)
        other_browse = QPushButton("Обзор...")
        other_browse.clicked.connect(self.browse_other)
        other_layout = QHBoxLayout()
        other_layout.addWidget(self.other_path_edit)
        other_layout.addWidget(other_browse)
        source_layout.addLayout(other_layout)

        self.source_other.toggled.connect(self.other_path_edit.setEnabled)
        source_group.setLayout(source_layout)
        layout.addWidget(source_group)

        # Кнопка загрузки классов
        load_btn_layout = QHBoxLayout()
        self.load_classes_btn = QPushButton("Загрузить классы из проекта")
        self.load_classes_btn.clicked.connect(self.load_classes)
        load_btn_layout.addWidget(self.load_classes_btn)
        layout.addLayout(load_btn_layout)

        # Группа для отображения иерархии классов (только просмотр)
        hierarchy_group = QGroupBox("Иерархия классов (из проекта)")
        hierarchy_layout = QVBoxLayout()
        self.hierarchy_tree = ClassHierarchyWidget()
        self.hierarchy_tree.setHeaderLabels(["Класс / Группа", "Количество"])
        self.hierarchy_tree.setColumnWidth(0, 250)
        self.hierarchy_tree.setColumnWidth(1, 80)
        self.hierarchy_tree.setDragEnabled(False)
        self.hierarchy_tree.setAcceptDrops(False)
        self.hierarchy_tree.setSelectionMode(QAbstractItemView.NoSelection)
        hierarchy_layout.addWidget(self.hierarchy_tree)
        hierarchy_group.setLayout(hierarchy_layout)
        layout.addWidget(hierarchy_group)

        # Опция использования суперклассов
        self.use_superclass_check = QCheckBox("Использовать суперклассы (объединять в группы)")
        self.use_superclass_check.setChecked(False)
        self.use_superclass_check.setToolTip("Если включено, каждый класс заменяется именем его родительской группы.\nЕсли класс не в группе, остаётся как есть.")
        layout.addWidget(self.use_superclass_check)

        # Разбиение
        split_group = QGroupBox("Разбиение на выборки")
        split_layout = QVBoxLayout()

        train_layout = QHBoxLayout()
        train_layout.addWidget(QLabel("Train:"))
        self.train_spin = QDoubleSpinBox()
        self.train_spin.setRange(0.0, 1.0)
        self.train_spin.setSingleStep(0.05)
        self.train_spin.setValue(0.8)
        self.train_spin.valueChanged.connect(self.on_split_changed)
        train_layout.addWidget(self.train_spin)
        train_layout.addStretch()
        split_layout.addLayout(train_layout)

        val_layout = QHBoxLayout()
        val_layout.addWidget(QLabel("Validation:"))
        self.val_spin = QDoubleSpinBox()
        self.val_spin.setRange(0.0, 1.0)
        self.val_spin.setSingleStep(0.05)
        self.val_spin.setValue(0.2)
        self.val_spin.valueChanged.connect(self.on_split_changed)
        val_layout.addWidget(self.val_spin)
        val_layout.addStretch()
        split_layout.addLayout(val_layout)

        test_layout = QHBoxLayout()
        test_layout.addWidget(QLabel("Test (остаток):"))
        self.test_spin = QDoubleSpinBox()
        self.test_spin.setRange(0.0, 1.0)
        self.test_spin.setSingleStep(0.05)
        self.test_spin.setValue(0.0)
        self.test_spin.setReadOnly(True)
        self.test_spin.setButtonSymbols(QDoubleSpinBox.NoButtons)
        test_layout.addWidget(self.test_spin)
        test_layout.addStretch()
        split_layout.addLayout(test_layout)

        split_group.setLayout(split_layout)
        layout.addWidget(split_group)

        # Дополнительные настройки для классификации
        self.classif_group = QGroupBox("Настройки классификации")
        classif_layout = QVBoxLayout()

        self.crop_boxes_check = QCheckBox("Вырезать объекты (crop boxes)")
        self.crop_boxes_check.setChecked(True)
        classif_layout.addWidget(self.crop_boxes_check)

        multi_layout = QHBoxLayout()
        multi_layout.addWidget(QLabel("Если несколько боксов на изображении:"))
        self.multi_combo = QComboBox()
        self.multi_combo.addItem("Использовать первый", "first")
        self.multi_combo.addItem("Пропускать", "skip")
        self.multi_combo.addItem("Предупреждать и использовать первый", "warn")
        multi_layout.addWidget(self.multi_combo)
        multi_layout.addStretch()
        classif_layout.addLayout(multi_layout)

        self.classif_group.setLayout(classif_layout)
        layout.addWidget(self.classif_group)
        self.classif_group.setVisible(False)

        # Путь для сохранения датасета
        dest_group = QGroupBox("Папка для сохранения датасета")
        dest_layout = QHBoxLayout()
        self.dest_edit = QLineEdit()
        self.dest_edit.setPlaceholderText("Выберите папку...")
        dest_browse = QPushButton("Обзор...")
        dest_browse.clicked.connect(self.browse_dest)
        dest_layout.addWidget(self.dest_edit)
        dest_layout.addWidget(dest_browse)
        dest_group.setLayout(dest_layout)
        layout.addWidget(dest_group)

        # Кнопки
        btn_layout = QHBoxLayout()
        self.create_btn = QPushButton("Создать датасет")
        self.create_btn.clicked.connect(self.create_dataset)
        self.cancel_btn = QPushButton("Отмена")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(self.create_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

        self.on_split_changed()

    def on_task_changed(self):
        is_classif = self.task_classification.isChecked()
        self.classif_group.setVisible(is_classif)

    def browse_other(self):
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку проекта")
        if folder:
            self.other_path_edit.setText(folder)

    def browse_dest(self):
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку для сохранения датасета")
        if folder:
            self.dest_edit.setText(folder)

    def on_split_changed(self):
        train = self.train_spin.value()
        val = self.val_spin.value()
        if train + val > 1.0:
            excess = train + val - 1.0
            self.train_spin.setValue(train - excess/2)
            self.val_spin.setValue(val - excess/2)
            train = self.train_spin.value()
            val = self.val_spin.value()
        test = 1.0 - train - val
        self.test_spin.setValue(test)

    def get_selected_project(self):
        if self.source_main.isChecked():
            return self.main_window.main_project
        elif self.source_auto.isChecked():
            return self.main_window.auto_project
        else:
            folder = self.other_path_edit.text().strip()
            if not folder or not os.path.isdir(folder):
                QMessageBox.warning(self, "Ошибка", "Укажите существующую папку проекта.")
                return None
            json_path = os.path.join(folder, "annotations.json")
            if not os.path.exists(json_path):
                QMessageBox.warning(self, "Ошибка", "В папке нет файла annotations.json.")
                return None
            return Project(folder, json_path)

    def load_classes(self):
        project = self.get_selected_project()
        if project is None:
            return
        project.load()
        counts = {}
        for boxes in project.annotations.values():
            for box in boxes:
                cls = box.get('class', 'unknown')
                counts[cls] = counts.get(cls, 0) + 1
        self.hierarchy_tree.populate_from_hierarchy(project.class_hierarchy, project.class_colors, counts)

    def create_dataset(self):
        dest = self.dest_edit.text().strip()
        if not dest:
            QMessageBox.warning(self, "Ошибка", "Укажите папку для сохранения датасета.")
            return

        project = self.get_selected_project()
        if project is None:
            return
        project.load()

        train_ratio = self.train_spin.value()
        val_ratio = self.val_spin.value()
        test_ratio = self.test_spin.value()
        is_classification = self.task_classification.isChecked()
        use_superclass = self.use_superclass_check.isChecked()

        class_mapping = {}
        if use_superclass:
            def process_item(item, parent_name=None):
                if item.data(0, Qt.UserRole) == "class":
                    orig_name = item.text(0)
                    if parent_name:
                        class_mapping[orig_name] = parent_name
                else:
                    group_name = item.text(0)
                    for i in range(item.childCount()):
                        process_item(item.child(i), group_name)
            root = self.hierarchy_tree.invisibleRootItem()
            for i in range(root.childCount()):
                process_item(root.child(i))

        try:
            progress = QProgressDialog("Подготовка датасета...", "Отмена", 0, 0, self)
            progress.setWindowModality(Qt.WindowModal)
            progress.setCancelButton(None)
            progress.show()

            if is_classification:
                crop_boxes = self.crop_boxes_check.isChecked()
                handling = self.multi_combo.currentData()
                train_cnt, val_cnt, test_cnt = prepare_classification_dataset(
                    project, dest, train_ratio, val_ratio, test_ratio,
                    class_mapping=class_mapping,
                    crop_boxes=crop_boxes,
                    multiple_boxes_handling=handling,
                    excluded_classes=set()
                )
                progress.close()
                msg = (f"Датасет классификации создан.\n"
                       f"Train: {train_cnt} изображений\n"
                       f"Val: {val_cnt} изображений\n"
                       f"Test: {test_cnt} изображений\n\n"
                       f"Образцы сохранены в {dest}")
            else:
                train_cnt, val_cnt, test_cnt = prepare_detection_dataset(
                    project, dest, train_ratio, val_ratio, test_ratio,
                    class_mapping=class_mapping
                )
                progress.close()
                msg = (f"Датасет детекции создан.\n"
                       f"Train: {train_cnt} изображений\n"
                       f"Val: {val_cnt} изображений\n"
                       f"Test: {test_cnt} изображений\n\n"
                       f"Файл data.yaml сохранён в {dest}")

            QMessageBox.information(self, "Готово", msg)
            self.accept()
        except Exception as e:
            progress.close()
            QMessageBox.critical(self, "Ошибка", f"Не удалось создать датасет:\n{str(e)}")