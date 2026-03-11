# ui/batch_dialog.py
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QDoubleSpinBox, QCheckBox, QPushButton, QGroupBox,
                             QProgressBar, QDialogButtonBox, QRadioButton,
                             QLineEdit, QFileDialog)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from ui.theme import DARK_STYLE

class BatchDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Пакетная разметка")
        self.setModal(True)
        self.setMinimumWidth(500)
        self.setStyleSheet(DARK_STYLE)

        layout = QVBoxLayout(self)

        # --- Источник изображений ---
        source_group = QGroupBox("Источник изображений")
        source_layout = QVBoxLayout()

        self.source_project = QRadioButton("Весь текущий проект")
        self.source_folder = QRadioButton("Выбрать папку")
        self.source_project.setChecked(True)
        source_layout.addWidget(self.source_project)
        source_layout.addWidget(self.source_folder)

        self.folder_edit = QLineEdit()
        self.folder_edit.setPlaceholderText("Путь к папке с изображениями")
        self.folder_edit.setEnabled(False)
        self.folder_browse = QPushButton("Обзор...")
        self.folder_browse.setEnabled(False)
        self.folder_browse.clicked.connect(self.browse_folder)

        folder_layout = QHBoxLayout()
        folder_layout.addWidget(self.folder_edit)
        folder_layout.addWidget(self.folder_browse)
        source_layout.addLayout(folder_layout)

        self.source_folder.toggled.connect(self.folder_edit.setEnabled)
        self.source_folder.toggled.connect(self.folder_browse.setEnabled)

        source_group.setLayout(source_layout)
        layout.addWidget(source_group)

        # --- Параметры детекции ---
        det_group = QGroupBox("Параметры детекции")
        det_layout = QVBoxLayout()

        conf_layout = QHBoxLayout()
        conf_layout.addWidget(QLabel("Confidence:"))
        self.conf_spin = QDoubleSpinBox()
        self.conf_spin.setRange(0.01, 1.0)
        self.conf_spin.setSingleStep(0.05)
        self.conf_spin.setValue(0.25)
        conf_layout.addWidget(self.conf_spin)
        conf_layout.addStretch()
        det_layout.addLayout(conf_layout)

        iou_layout = QHBoxLayout()
        iou_layout.addWidget(QLabel("IOU:"))
        self.iou_spin = QDoubleSpinBox()
        self.iou_spin.setRange(0.01, 1.0)
        self.iou_spin.setSingleStep(0.05)
        self.iou_spin.setValue(0.5)
        iou_layout.addWidget(self.iou_spin)
        iou_layout.addStretch()
        det_layout.addLayout(iou_layout)

        det_group.setLayout(det_layout)
        layout.addWidget(det_group)

        # --- Классификатор ---
        cls_group = QGroupBox("Классификатор")
        cls_layout = QVBoxLayout()

        self.use_cls_check = QCheckBox("Использовать классификатор для уточнения класса")
        self.use_cls_check.setChecked(True)
        cls_layout.addWidget(self.use_cls_check)

        cls_conf_layout = QHBoxLayout()
        cls_conf_layout.addWidget(QLabel("Порог классификатора:"))
        self.cls_conf_spin = QDoubleSpinBox()
        self.cls_conf_spin.setRange(0.01, 1.0)
        self.cls_conf_spin.setSingleStep(0.05)
        self.cls_conf_spin.setValue(0.5)
        cls_conf_layout.addWidget(self.cls_conf_spin)
        cls_conf_layout.addStretch()
        cls_layout.addLayout(cls_conf_layout)

        cls_group.setLayout(cls_layout)
        layout.addWidget(cls_group)

        # --- Кнопки ---
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку с изображениями")
        if folder:
            self.folder_edit.setText(folder)

    def get_params(self):
        return {
            "source_type": "project" if self.source_project.isChecked() else "folder",
            "source_path": self.folder_edit.text().strip() if self.source_folder.isChecked() else None,
            "conf": self.conf_spin.value(),
            "iou": self.iou_spin.value(),
            "use_classifier": self.use_cls_check.isChecked(),
            "cls_conf": self.cls_conf_spin.value()
        }


class ProgressDialog(QDialog):
    """Диалог с прогресс-баром для отображения хода пакетной обработки."""
    cancelled = pyqtSignal()

    def __init__(self, total, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Пакетная разметка")
        self.setModal(True)
        self.setFixedSize(400, 150)
        self.setStyleSheet(DARK_STYLE)

        layout = QVBoxLayout(self)

        self.label = QLabel("Обработка изображений...")
        layout.addWidget(self.label)

        self.progress = QProgressBar()
        self.progress.setRange(0, total)
        layout.addWidget(self.progress)

        self.cancel_btn = QPushButton("Отмена")
        self.cancel_btn.clicked.connect(self.on_cancel)
        layout.addWidget(self.cancel_btn)

    def on_cancel(self):
        self.cancelled.emit()
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.setText("Отменяется...")

    def update_progress(self, value, filename):
        self.progress.setValue(value + 1)  # value - текущий индекс (0-based)
        self.label.setText(f"Обработка: {filename}")