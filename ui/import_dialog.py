# ui/import_dialog.py
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QComboBox, QLineEdit, QPushButton, QFileDialog,
                             QGroupBox, QRadioButton, QMessageBox)
from ui.theme import get_current_theme_style
from project.importers import import_yolo, import_coco, import_voc
from core.i18n import tr

class ImportDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("Импорт аннотаций"))
        self.setModal(True)
        self.setMinimumWidth(520)
        self.setStyleSheet(get_current_theme_style())

        self.result_data = None

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # ── Формат ──────────────────────────────────────────────
        fmt_layout = QHBoxLayout()
        fmt_layout.addWidget(QLabel(tr("Формат:")))
        self.format_combo = QComboBox()
        self.format_combo.addItems(["YOLO", "COCO", "Pascal VOC"])
        self.format_combo.currentTextChanged.connect(self._on_format_changed)
        fmt_layout.addWidget(self.format_combo)
        fmt_layout.addStretch()
        layout.addLayout(fmt_layout)

        # ── Источник ─────────────────────────────────────────────
        src_layout = QHBoxLayout()
        src_layout.addWidget(QLabel(tr("Источник:")))
        self.source_edit = QLineEdit()
        self.source_edit.setPlaceholderText(tr("Путь к папке или файлу"))
        src_layout.addWidget(self.source_edit)
        self.browse_btn = QPushButton(tr("Обзор..."))
        self.browse_btn.clicked.connect(self.browse)
        src_layout.addWidget(self.browse_btn)
        layout.addLayout(src_layout)

        self.hint_label = QLabel(tr("YOLO: папка содержащая labels/ и classes.txt"))
        self.hint_label.setStyleSheet("color: #71717a; font-size: 11px;")
        layout.addWidget(self.hint_label)

        # ── Конфликты ────────────────────────────────────────────
        conflict_group = QGroupBox(tr("При совпадении аннотаций"))
        conflict_layout = QHBoxLayout()
        self.merge_radio = QRadioButton(tr("Объединить (добавить к существующим)"))
        self.overwrite_radio = QRadioButton(tr("Заменить существующие"))
        self.merge_radio.setChecked(True)
        conflict_layout.addWidget(self.merge_radio)
        conflict_layout.addWidget(self.overwrite_radio)
        conflict_group.setLayout(conflict_layout)
        layout.addWidget(conflict_group)

        # ── Кнопки ───────────────────────────────────────────────
        btn_layout = QHBoxLayout()
        self.import_btn = QPushButton(tr("Импортировать"))
        self.import_btn.clicked.connect(self.do_import)
        self.cancel_btn = QPushButton(tr("Отмена"))
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(self.import_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

    def _on_format_changed(self, fmt):
        hints = {
            "YOLO":       tr("YOLO: папка содержащая labels/ и classes.txt"),
            "COCO":       tr("COCO: JSON-файл с аннотациями"),
            "Pascal VOC": tr("Pascal VOC: папка с XML-файлами"),
        }
        self.hint_label.setText(hints.get(fmt, ""))

    def browse(self):
        fmt = self.format_combo.currentText()
        if fmt == "COCO":
            path, _ = QFileDialog.getOpenFileName(
                self, tr("Выберите COCO JSON"), "", "JSON files (*.json)")
        elif fmt == "Pascal VOC":
            path = QFileDialog.getExistingDirectory(
                self, tr("Выберите папку с XML-файлами"))
        else:
            path = QFileDialog.getExistingDirectory(
                self, tr("Выберите корневую папку YOLO (с labels/ и classes.txt)"))
        if path:
            self.source_edit.setText(path)

    def do_import(self):
        source = self.source_edit.text().strip()
        fmt = self.format_combo.currentText()
        if not source:
            QMessageBox.warning(self, tr("Ошибка"), tr("Укажите источник."))
            return

        try:
            if fmt == "YOLO":
                data, classes = import_yolo(source)
            elif fmt == "COCO":
                data, classes = import_coco(source)
            else:
                data, classes = import_voc(source)
        except Exception as e:
            QMessageBox.critical(
                self, tr("Ошибка импорта"),
                f"{tr('Не удалось импортировать')}:\n{str(e)}")
            return

        if not data:
            QMessageBox.information(self, tr("Импорт"), tr("Не найдено аннотаций."))
            return

        self.result_data = (data, classes, self.merge_radio.isChecked())
        self.accept()