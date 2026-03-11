# ui/import_dialog.py
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QComboBox, QLineEdit, QPushButton, QFileDialog,
                             QGroupBox, QRadioButton, QMessageBox)
from ui.theme import DARK_STYLE

class ImportDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Импорт аннотаций")
        self.setModal(True)
        self.setMinimumWidth(500)
        self.setStyleSheet(DARK_STYLE)

        self.result_data = None  # (annotations_dict, classes_list)

        layout = QVBoxLayout(self)

        # Формат
        fmt_layout = QHBoxLayout()
        fmt_layout.addWidget(QLabel("Формат:"))
        self.format_combo = QComboBox()
        self.format_combo.addItems(["YOLO", "COCO", "Pascal VOC"])
        fmt_layout.addWidget(self.format_combo)
        fmt_layout.addStretch()
        layout.addLayout(fmt_layout)

        # Источник
        src_layout = QHBoxLayout()
        src_layout.addWidget(QLabel("Источник:"))
        self.source_edit = QLineEdit()
        self.source_edit.setPlaceholderText("Путь к папке или файлу")
        src_layout.addWidget(self.source_edit)
        self.browse_btn = QPushButton("Обзор...")
        self.browse_btn.clicked.connect(self.browse)
        src_layout.addWidget(self.browse_btn)
        layout.addLayout(src_layout)

        # Действие
        action_group = QGroupBox("Действие")
        action_layout = QHBoxLayout()
        self.add_radio = QRadioButton("Добавить к текущему проекту")
        self.new_radio = QRadioButton("Создать новый проект")
        self.add_radio.setChecked(True)
        action_layout.addWidget(self.add_radio)
        action_layout.addWidget(self.new_radio)
        action_group.setLayout(action_layout)
        layout.addWidget(action_group)

        # Кнопки
        btn_layout = QHBoxLayout()
        self.import_btn = QPushButton("Импортировать")
        self.import_btn.clicked.connect(self.do_import)
        self.cancel_btn = QPushButton("Отмена")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(self.import_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

    def browse(self):
        fmt = self.format_combo.currentText()
        if fmt == "COCO":
            path, _ = QFileDialog.getOpenFileName(self, "Выберите COCO JSON", "", "JSON files (*.json)")
        elif fmt == "Pascal VOC":
            path = QFileDialog.getExistingDirectory(self, "Выберите папку с XML-файлами")
        else:  # YOLO
            path = QFileDialog.getExistingDirectory(self, "Выберите корневую папку (с images и labels)")
        if path:
            self.source_edit.setText(path)

    def do_import(self):
        source = self.source_edit.text().strip()
        fmt = self.format_combo.currentText()
        if not source:
            QMessageBox.warning(self, "Ошибка", "Укажите источник.")
            return

        try:
            if fmt == "YOLO":
                data, classes = import_yolo(source)
            elif fmt == "COCO":
                data, classes = import_coco(source)
            else:  # VOC
                data, classes = import_voc(source)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка импорта", f"Не удалось импортировать:\n{str(e)}")
            return

        if not data:
            QMessageBox.information(self, "Импорт", "Не найдено аннотаций.")
            return

        self.result_data = (data, classes)
        self.accept()