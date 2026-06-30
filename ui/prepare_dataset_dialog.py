# ui/prepare_dataset_dialog.py
import os
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QDoubleSpinBox, QPushButton, QGroupBox,
                             QRadioButton, QFileDialog, QMessageBox, QProgressDialog,
                             QComboBox, QCheckBox, QAbstractItemView, QLineEdit)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from ui.theme import get_current_theme_style
from project.dataset_preparer import prepare_detection_dataset, prepare_classification_dataset
from project.project_manager import Project
from ui.class_hierarchy_widget import ClassHierarchyWidget
from core.i18n import tr

class PrepareWorker(QThread):
    progress_val = pyqtSignal(int, int) # current, total
    finished = pyqtSignal(bool, str, object) # success, message, counts (tuple)
    
    def __init__(self, task_type, params):
        super().__init__()
        self.task_type = task_type # 'detection', 'segmentation' or 'classification'
        self.params = params
        
    def run(self):
        try:
            if self.task_type in ('detection', 'segmentation'):
                # prepare_detection_dataset expects task_type as parameter
                counts = prepare_detection_dataset(
                    **self.params, 
                    progress_callback=self.progress_val.emit
                )
            else:
                # prepare_classification_dataset
                counts = prepare_classification_dataset(
                    **self.params,
                    progress_callback=self.progress_val.emit
                )
            self.finished.emit(True, "", counts)
        except Exception as e:
            self.finished.emit(False, str(e), (0, 0, 0))

class PrepareDatasetDialog(QDialog):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.setWindowTitle(tr("Подготовка датасета"))
        self.setModal(True)
        self.setMinimumWidth(900)
        self.setMinimumHeight(720)
        self.setStyleSheet(get_current_theme_style())

        layout = QVBoxLayout(self)

        # Тип задачи
        task_group = QGroupBox(tr("Тип задачи"))
        task_layout = QHBoxLayout()
        self.task_detection = QRadioButton(tr("Детекция"))
        self.task_segmentation = QRadioButton(tr("Сегментация"))
        self.task_classification = QRadioButton(tr("Классификация"))
        self.task_detection.setChecked(True)
        self.task_detection.toggled.connect(self.on_task_changed)
        self.task_segmentation.toggled.connect(self.on_task_changed)

        task_layout.addWidget(self.task_detection)
        task_layout.addWidget(self.task_segmentation)
        task_layout.addWidget(self.task_classification)
        task_layout.addStretch()
        task_group.setLayout(task_layout)
        layout.addWidget(task_group)

        # Выбор проекта
        source_group = QGroupBox(tr("Исходный проект"))
        source_layout = QVBoxLayout()
        self.source_main = QRadioButton(tr("Основной проект"))
        self.source_auto = QRadioButton(tr("Авто-проект"))
        self.source_other = QRadioButton(tr("Другая папка"))
        self.source_main.setChecked(True)
        source_layout.addWidget(self.source_main)
        source_layout.addWidget(self.source_auto)
        source_layout.addWidget(self.source_other)

        self.other_path_edit = QLineEdit()
        self.other_path_edit.setPlaceholderText(tr("Путь к папке с изображениями и annotations.json"))
        self.other_path_edit.setEnabled(False)
        other_browse = QPushButton(tr("Обзор..."))
        other_browse.clicked.connect(self.browse_other)
        other_layout = QHBoxLayout()
        other_layout.addWidget(self.other_path_edit)
        other_layout.addWidget(other_browse)
        source_layout.addLayout(other_layout)

        self.source_other.toggled.connect(self.other_path_edit.setEnabled)
        source_group.setLayout(source_layout)
        layout.addWidget(source_group)

        # Выбор классов для иерархии
        self.class_group = QGroupBox(tr("Выбор классов"))
        class_layout = QVBoxLayout()
        self.class_tree = ClassHierarchyWidget()
        class_layout.addWidget(self.class_tree)
        
        self.merge_checkbox = QCheckBox(tr("Объединить в мегаклассы (по верхнему родителю)"))
        self.merge_checkbox.setChecked(True)
        class_layout.addWidget(self.merge_checkbox)
        
        self.class_group.setLayout(class_layout)
        layout.addWidget(self.class_group)

        # Настройки разбиения
        split_group = QGroupBox(tr("Разбиение данных"))
        split_layout = QHBoxLayout()
        split_layout.addWidget(QLabel(tr("Train:")))
        self.train_spin = QDoubleSpinBox()
        self.train_spin.setRange(0.1, 1.0)
        self.train_spin.setValue(0.8)
        self.train_spin.setSingleStep(0.05)
        split_layout.addWidget(self.train_spin)

        split_layout.addWidget(QLabel(tr("Val:")))
        self.val_spin = QDoubleSpinBox()
        self.val_spin.setRange(0.0, 0.5)
        self.val_spin.setValue(0.2)
        self.val_spin.setSingleStep(0.05)
        split_layout.addWidget(self.val_spin)

        split_layout.addWidget(QLabel(tr("Test:")))
        self.test_spin = QDoubleSpinBox()
        self.test_spin.setRange(0.0, 0.5)
        self.test_spin.setValue(0.0)
        self.test_spin.setSingleStep(0.05)
        split_layout.addWidget(self.test_spin)

        split_group.setLayout(split_layout)
        layout.addWidget(split_group)

        # Выходная папка
        out_group = QGroupBox(tr("Выходная папка"))
        out_layout = QHBoxLayout()
        self.output_edit = QLineEdit()
        self.output_edit.setText(os.path.join(os.getcwd(), "dataset_export"))
        out_browse = QPushButton(tr("Обзор..."))
        out_browse.clicked.connect(self.browse_output)
        out_layout.addWidget(self.output_edit)
        out_layout.addWidget(out_browse)
        out_group.setLayout(out_layout)
        layout.addWidget(out_group)

        # Кнопки
        btn_layout = QHBoxLayout()
        self.prepare_btn = QPushButton(tr("Подготовить"))
        self.prepare_btn.clicked.connect(self.run_prepare)
        self.prepare_btn.setMinimumHeight(40)
        self.prepare_btn.setStyleSheet("font-weight: bold; background-color: #2e7d32; color: white;")
        cancel_btn = QPushButton(tr("Отмена"))
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setMinimumHeight(40)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(self.prepare_btn)
        layout.addLayout(btn_layout)

        # Инициализация списка классов
        self.update_classes()
        self.source_main.toggled.connect(self.update_classes)
        self.source_auto.toggled.connect(self.update_classes)
        self.other_path_edit.textChanged.connect(self.update_classes)

    def on_task_changed(self):
        is_cls = self.task_classification.isChecked()
        self.class_group.setVisible(not is_cls)
        self.update_classes()

    def browse_other(self):
        folder = QFileDialog.getExistingDirectory(self, tr("Выберите папку с проектом"))
        if folder:
            self.other_path_edit.setText(folder)

    def browse_output(self):
        folder = QFileDialog.getExistingDirectory(self, tr("Выберите папку для сохранения датасета"))
        if folder:
            self.output_edit.setText(folder)

    def update_classes(self):
        project = self.get_project()
        if project:
            if self.task_classification.isChecked():
                self.class_tree.populate_from_hierarchy([], {}, {})
            else:
                self.class_tree.populate_from_hierarchy(
                    project.class_hierarchy,
                    project.class_colors,
                    {}
                )

    def get_project(self):
        if self.source_main.isChecked():
            return self.main_window.main_project
        elif self.source_auto.isChecked():
            return self.main_window.auto_project
        else:
            path = self.other_path_edit.text()
            if os.path.exists(path):
                try:
                    return Project(path, os.path.join(path, "annotations.json"))
                except:
                    return None
        return None

    def run_prepare(self):
        project = self.get_project()
        if not project:
            QMessageBox.warning(self, tr("Ошибка"), tr("Проект не найден или некорректен"))
            return

        out_dir = self.output_edit.text()
        if not out_dir:
            QMessageBox.warning(self, tr("Ошибка"), tr("Укажите выходную папку"))
            return

        # Проверяем сумму весов
        total = self.train_spin.value() + self.val_spin.value() + self.test_spin.value()
        if abs(total - 1.0) > 0.001:
            QMessageBox.warning(self, tr("Ошибка"), tr("Сумма долей Train, Val, Test должна быть равна 1.0"))
            return

        selected_mapping = self.class_tree.get_mapping(merge_to_parent=self.merge_checkbox.isChecked())
        excluded_classes = self.class_tree.get_excluded_classes()
        
        if not self.task_classification.isChecked() and not selected_mapping:
            QMessageBox.warning(self, tr("Ошибка"), tr("Выберите хотя бы один класс для экспорта"))
            return

        self.progress = QProgressDialog(tr("Подготовка датасета..."), tr("Отмена"), 0, 100, self)
        self.progress.setWindowModality(Qt.WindowModal)
        self.progress.setAutoClose(True)
        self.progress.show()

        # Параметры для воркера
        params = {
            "project": project,
            "output_dir": out_dir,
            "train_ratio": self.train_spin.value(),
            "val_ratio": self.val_spin.value(),
            "test_ratio": self.test_spin.value(),
            "class_mapping": selected_mapping,
            "excluded_classes": excluded_classes
        }

        if self.task_detection.isChecked() or self.task_segmentation.isChecked():
            task_type = 'segmentation' if self.task_segmentation.isChecked() else 'detection'
            params["task_type"] = task_type
        else:
            task_type = 'classification'

        self.worker = PrepareWorker(task_type, params)
        self.worker.progress_val.connect(self.on_progress)
        self.worker.finished.connect(self.on_finished)
        self.worker.start()

    def on_progress(self, current, total):
        if total > 0:
            val = int(current / total * 100)
            self.progress.setValue(val)
            self.progress.setLabelText(f"{tr('Обработка')}... {current}/{total}")

    def on_finished(self, success, message, counts):
        self.progress.close()
        if success:
            train_count, val_count, test_count = counts
            msg = f"{tr('Датасет успешно подготовлен!')}\n\n" \
                  f"{tr('Train')}: {train_count}\n" \
                  f"{tr('Val')}: {val_count}\n" \
                  f"{tr('Test')}: {test_count}\n\n" \
                  f"{tr('Путь')}: {self.output_edit.text()}"
            QMessageBox.information(self, tr("Готово"), msg)
            self.accept()
        else:
            QMessageBox.critical(self, tr("Ошибка"), f"{tr('Ошибка при подготовке датасета')}: {message}")