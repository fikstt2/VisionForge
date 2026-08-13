# ui/prepare_dataset_dialog.py
import os
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QDoubleSpinBox, QPushButton, QGroupBox,
                             QRadioButton, QFileDialog, QMessageBox, QProgressDialog,
                             QComboBox, QCheckBox, QAbstractItemView, QLineEdit, QWidget)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from ui.theme import get_current_theme_style
from project.dataset_preparer import prepare_detection_dataset, prepare_classification_dataset
from project.project_manager import Project
from ui.class_hierarchy_widget import ClassHierarchyWidget
from core.i18n import tr

class PrepareWorker(QThread):
    progress_val = pyqtSignal(int, int)         # current, total
    finished = pyqtSignal(bool, str, object)    # success, message, counts (tuple)

    def __init__(self, task_type, params):
        super().__init__()
        self.task_type = task_type  # 'detection', 'segmentation' or 'classification'
        self.params = params

    def run(self):
        try:
            if self.task_type in ('detection', 'segmentation'):
                counts = prepare_detection_dataset(
                    **self.params,
                    progress_callback=self.progress_val.emit
                )
            else:
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
        self.setMinimumHeight(760)
        self.setStyleSheet(get_current_theme_style())

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # ── Тип задачи ────────────────────────────────────────────────────────
        task_group = QGroupBox(tr("Тип задачи"))
        task_layout = QHBoxLayout()
        self.task_detection = QRadioButton(tr("Детекция"))
        self.task_segmentation = QRadioButton(tr("Сегментация"))
        self.task_classification = QRadioButton(tr("Классификация"))
        self.task_detection.setChecked(True)
        self.task_detection.toggled.connect(self.on_task_changed)
        self.task_segmentation.toggled.connect(self.on_task_changed)
        self.task_classification.toggled.connect(self.on_task_changed)
        task_layout.addWidget(self.task_detection)
        task_layout.addWidget(self.task_segmentation)
        task_layout.addWidget(self.task_classification)
        task_layout.addStretch()
        task_group.setLayout(task_layout)
        layout.addWidget(task_group)

        # ── Режим аннотаций ───────────────────────────────────────────────────
        # Теперь один проект, но выбор источника разметки: ручная (main) или авто-разметка ИИ (auto)
        mode_group = QGroupBox(tr("Источник аннотаций"))
        mode_layout = QHBoxLayout()
        self.mode_main_radio = QRadioButton(tr("Ручная разметка (main)"))
        self.mode_auto_radio = QRadioButton(tr("Авто-разметка ИИ (auto)"))
        self.mode_main_radio.setChecked(True)
        mode_layout.addWidget(self.mode_main_radio)
        mode_layout.addWidget(self.mode_auto_radio)
        mode_layout.addStretch()
        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)

        # ── Внешний проект (другой .vf файл) ─────────────────────────────────
        other_group = QGroupBox(tr("Использовать другой проект .vf (необязательно)"))
        other_group.setCheckable(True)
        other_group.setChecked(False)
        self.other_project_group = other_group
        other_layout = QHBoxLayout()
        self.other_path_edit = QLineEdit()
        self.other_path_edit.setPlaceholderText(tr("Путь к файлу .vf другого проекта"))
        other_browse = QPushButton(tr("Обзор..."))
        other_browse.clicked.connect(self.browse_other)
        other_layout.addWidget(self.other_path_edit)
        other_layout.addWidget(other_browse)
        other_group.setLayout(other_layout)
        other_group.toggled.connect(self.update_classes)
        self.other_path_edit.textChanged.connect(self.update_classes)
        layout.addWidget(other_group)

        # ── Выбор классов ─────────────────────────────────────────────────────
        self.class_group = QGroupBox(tr("Выбор классов"))
        class_layout = QVBoxLayout()
        self.class_tree = ClassHierarchyWidget()
        class_layout.addWidget(self.class_tree)
        self.merge_checkbox = QCheckBox(tr("Объединить в мегаклассы (по верхнему родителю)"))
        self.merge_checkbox.setChecked(True)
        class_layout.addWidget(self.merge_checkbox)
        self.class_group.setLayout(class_layout)
        layout.addWidget(self.class_group)

        # ── Настройки сегментации ─────────────────────────────────────────────
        self.seg_group = QGroupBox(tr("Обработка bounding-box при сегментации"))
        seg_layout = QVBoxLayout()
        self.seg_box_exclude = QRadioButton(
            tr("Пропустить bbox-only аннотации (только полигоны)"))
        self.seg_box_exclude.setChecked(True)
        self.seg_box_exclude.setToolTip(tr(
            "Рекомендуется: в датасет попадут только изображения с реальными полигонами"))
        self.seg_box_convert = QRadioButton(
            tr("Конвертировать bbox → прямоугольный полигон (4 точки)"))
        self.seg_box_convert.setToolTip(tr(
            "Bbox преобразуется в полигон из 4 вершин. Допустимо для старых аннотаций"))
        self.seg_box_keep = QRadioButton(
            tr("Оставить bbox как есть (записать как 4-точечный полигон)"))
        self.seg_box_keep.setToolTip(tr(
            "Технически эквивалентно конвертации, но явно помечает намеренное решение"))
        seg_warn = QLabel(tr("⚠️ bbox-аннотации будут включены как прямоугольные маски"))
        seg_warn.setStyleSheet("color: #f59e0b; font-size: 11px;")
        seg_warn.setVisible(False)
        self.seg_box_keep.toggled.connect(seg_warn.setVisible)
        seg_layout.addWidget(self.seg_box_exclude)
        seg_layout.addWidget(self.seg_box_convert)
        seg_layout.addWidget(self.seg_box_keep)
        seg_layout.addWidget(seg_warn)
        self.seg_group.setLayout(seg_layout)
        self.seg_group.setVisible(False)
        layout.addWidget(self.seg_group)

        # ── Разбиение ─────────────────────────────────────────────────────────
        split_group = QGroupBox(tr("Разбиение данных"))
        split_layout = QHBoxLayout()
        split_layout.addWidget(QLabel("Train:"))
        self.train_spin = QDoubleSpinBox()
        self.train_spin.setRange(0.1, 1.0)
        self.train_spin.setValue(0.8)
        self.train_spin.setSingleStep(0.05)
        split_layout.addWidget(self.train_spin)
        split_layout.addWidget(QLabel("Val:"))
        self.val_spin = QDoubleSpinBox()
        self.val_spin.setRange(0.0, 0.5)
        self.val_spin.setValue(0.2)
        self.val_spin.setSingleStep(0.05)
        split_layout.addWidget(self.val_spin)
        split_layout.addWidget(QLabel("Test:"))
        self.test_spin = QDoubleSpinBox()
        self.test_spin.setRange(0.0, 0.5)
        self.test_spin.setValue(0.0)
        self.test_spin.setSingleStep(0.05)
        split_layout.addWidget(self.test_spin)
        split_layout.addStretch()
        split_group.setLayout(split_layout)
        layout.addWidget(split_group)

        # ── Выходная папка ────────────────────────────────────────────────────
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

        # ── Кнопки ───────────────────────────────────────────────────────────
        btn_layout = QHBoxLayout()
        cancel_btn = QPushButton(tr("Отмена"))
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setMinimumHeight(40)
        self.prepare_btn = QPushButton(tr("Подготовить"))
        self.prepare_btn.clicked.connect(self.run_prepare)
        self.prepare_btn.setMinimumHeight(40)
        self.prepare_btn.setStyleSheet("font-weight: bold; background-color: #2e7d32; color: white;")
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(self.prepare_btn)
        layout.addLayout(btn_layout)

        # Инициализация
        self.update_classes()
        self.mode_main_radio.toggled.connect(self.update_classes)

    def on_task_changed(self):
        is_cls = self.task_classification.isChecked()
        is_seg = self.task_segmentation.isChecked()
        self.class_group.setVisible(not is_cls)
        self.seg_group.setVisible(is_seg)
        self.update_classes()

    def browse_other(self):
        path, _ = QFileDialog.getOpenFileName(
            self, tr("Выберите файл проекта VisionForge"), "",
            "VisionForge Project (*.vf);;All files (*)")
        if path:
            self.other_path_edit.setText(path)

    def browse_output(self):
        folder = QFileDialog.getExistingDirectory(self, tr("Выберите папку для сохранения датасета"))
        if folder:
            self.output_edit.setText(folder)

    def get_project(self):
        """Возвращает объект Project: текущий открытый или указанный внешний .vf файл."""
        if self.other_project_group.isChecked():
            vf_path = self.other_path_edit.text().strip()
            if vf_path and os.path.exists(vf_path):
                try:
                    p = Project(vf_path)
                    p.load()
                    return p
                except Exception as e:
                    return None
            return None
        # Иначе — текущий открытый проект
        return self.main_window.project

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

    def run_prepare(self):
        project = self.get_project()
        if not project:
            QMessageBox.warning(self, tr("Ошибка"), tr("Проект не найден или некорректен.\nОткройте проект или укажите корректный .vf файл."))
            return

        out_dir = self.output_edit.text().strip()
        if not out_dir:
            QMessageBox.warning(self, tr("Ошибка"), tr("Укажите выходную папку"))
            return

        total = self.train_spin.value() + self.val_spin.value() + self.test_spin.value()
        if abs(total - 1.0) > 0.001:
            QMessageBox.warning(self, tr("Ошибка"),
                tr("Сумма долей Train + Val + Test должна равняться 1.0\n"
                   f"Текущая сумма: {total:.2f}"))
            return

        # Режим аннотаций
        mode = "auto" if self.mode_auto_radio.isChecked() else "main"

        # Параметры для воркера
        params = {
            "project":          project,
            "output_dir":       out_dir,
            "train_ratio":      self.train_spin.value(),
            "val_ratio":        self.val_spin.value(),
            "test_ratio":       self.test_spin.value(),
            "mode":             mode,
            "class_mapping":    self.class_tree.get_mapping(merge_to_parent=self.merge_checkbox.isChecked()),
            "excluded_classes": self.class_tree.get_excluded_classes(),
        }

        if self.task_detection.isChecked() or self.task_segmentation.isChecked():
            task_type = 'segmentation' if self.task_segmentation.isChecked() else 'detection'
            if not params["class_mapping"]:
                QMessageBox.warning(self, tr("Ошибка"), tr("Выберите хотя бы один класс для экспорта"))
                return
            if task_type == 'segmentation':
                if self.seg_box_convert.isChecked():
                    params["seg_box_mode"] = "convert"
                elif self.seg_box_keep.isChecked():
                    params["seg_box_mode"] = "keep"
                else:
                    params["seg_box_mode"] = "exclude"
        else:
            task_type = 'classification'

        self.progress = QProgressDialog(tr("Подготовка датасета..."), tr("Отмена"), 0, 100, self)
        self.progress.setWindowModality(Qt.WindowModal)
        self.progress.setAutoClose(True)
        self.progress.show()

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
            msg = (f"{tr('Датасет успешно подготовлен!')}\n\n"
                   f"Train: {train_count}\n"
                   f"Val:   {val_count}\n"
                   f"Test:  {test_count}\n\n"
                   f"{tr('Путь')}: {self.output_edit.text()}")
            QMessageBox.information(self, tr("Готово"), msg)
            self.accept()
        else:
            QMessageBox.critical(self, tr("Ошибка"),
                f"{tr('Ошибка при подготовке датасета')}:\n{message}")