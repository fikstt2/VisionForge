# ui/settings_dialog.py
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout,
                             QLineEdit, QPushButton, QFileDialog, QDoubleSpinBox,
                             QFormLayout, QDialogButtonBox, QTabWidget,
                             QCheckBox, QSpinBox, QWidget)
from ui.theme import DARK_STYLE
import config

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Настройки")
        self.setModal(True)
        self.resize(600, 450)
        self.setStyleSheet(DARK_STYLE)

        self.current_config = config.load_config()

        layout = QVBoxLayout(self)

        tabs = QTabWidget()
        layout.addWidget(tabs)

        # ---------- Вкладка "Модели" ----------
        model_tab = QWidget()
        model_layout = QFormLayout(model_tab)

        self.detector_path_edit = QLineEdit()
        self.detector_path_edit.setText(self.current_config["detector_path"])
        detector_browse = QPushButton("Обзор...")
        detector_browse.clicked.connect(lambda: self.browse_file(self.detector_path_edit, "Выберите файл детектора (*.pt)"))
        detector_layout = QHBoxLayout()
        detector_layout.addWidget(self.detector_path_edit)
        detector_layout.addWidget(detector_browse)
        model_layout.addRow("Детектор:", detector_layout)

        self.classifier_path_edit = QLineEdit()
        self.classifier_path_edit.setText(self.current_config["classifier_path"])
        classifier_browse = QPushButton("Обзор...")
        classifier_browse.clicked.connect(lambda: self.browse_file(self.classifier_path_edit, "Выберите файл классификатора (*.pt)"))
        classifier_layout = QHBoxLayout()
        classifier_layout.addWidget(self.classifier_path_edit)
        classifier_layout.addWidget(classifier_browse)
        model_layout.addRow("Классификатор:", classifier_layout)

        self.cls_conf_spin = QDoubleSpinBox()
        self.cls_conf_spin.setRange(0.0, 1.0)
        self.cls_conf_spin.setSingleStep(0.05)
        self.cls_conf_spin.setValue(self.current_config["cls_conf"])
        model_layout.addRow("Confidence классификатора:", self.cls_conf_spin)

        tabs.addTab(model_tab, "Модели")

        # ---------- Вкладка "Данные" ----------
        data_tab = QWidget()
        data_layout = QFormLayout(data_tab)

        self.main_images_dir_edit = QLineEdit()
        self.main_images_dir_edit.setText(self.current_config["main_images_dir"])
        main_images_browse = QPushButton("Обзор...")
        main_images_browse.clicked.connect(lambda: self.browse_folder(self.main_images_dir_edit, "Выберите папку с основными изображениями"))
        main_images_layout = QHBoxLayout()
        main_images_layout.addWidget(self.main_images_dir_edit)
        main_images_layout.addWidget(main_images_browse)
        data_layout.addRow("Папка изображений (основная):", main_images_layout)

        self.main_json_edit = QLineEdit()
        self.main_json_edit.setText(self.current_config["main_json"])
        main_json_browse = QPushButton("Обзор...")
        main_json_browse.clicked.connect(lambda: self.browse_file(self.main_json_edit, "Выберите файл аннотаций (main.json)", "*.json"))
        main_json_layout = QHBoxLayout()
        main_json_layout.addWidget(self.main_json_edit)
        main_json_layout.addWidget(main_json_browse)
        data_layout.addRow("Файл аннотаций (основной):", main_json_layout)

        self.auto_json_edit = QLineEdit()
        self.auto_json_edit.setText(self.current_config["auto_json"])
        auto_json_browse = QPushButton("Обзор...")
        auto_json_browse.clicked.connect(lambda: self.browse_file(self.auto_json_edit, "Выберите файл авто-аннотаций (auto.json)", "*.json"))
        auto_json_layout = QHBoxLayout()
        auto_json_layout.addWidget(self.auto_json_edit)
        auto_json_layout.addWidget(auto_json_browse)
        data_layout.addRow("Файл авто-аннотаций:", auto_json_layout)

        tabs.addTab(data_tab, "Данные")

        # Вкладка "Производительность"
        perf_tab = QWidget()
        perf_layout = QFormLayout(perf_tab)

        self.thumb_cache_check = QCheckBox("Использовать дисковый кэш миниатюр")
        self.thumb_cache_check.setChecked(self.current_config.get("thumbnail_cache", True))

        self.thumb_quality_spin = QSpinBox()
        self.thumb_quality_spin.setRange(1, 100)
        self.thumb_quality_spin.setValue(self.current_config.get("thumbnail_quality", 70))

        self.async_load_check = QCheckBox("Асинхронная загрузка изображений (экспериментально)")
        self.async_load_check.setChecked(self.current_config.get("async_image_loading", False))

        tabs.addTab(perf_tab, "Производительность")

        # ---------- Новая вкладка "Интерфейс" ----------
        ui_tab = QWidget()
        ui_layout = QFormLayout(ui_tab)

        self.auto_hide_check = QCheckBox("Автоматически скрывать правую панель в полноэкранном режиме")
        self.auto_hide_check.setChecked(self.current_config.get("auto_hide_panel", False))
        ui_layout.addRow(self.auto_hide_check)

        tabs.addTab(ui_tab, "Интерфейс")

        # ---------- Кнопки OK/Cancel ----------
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def browse_file(self, line_edit, title, filter="*.pt *.pth"):
        filename, _ = QFileDialog.getOpenFileName(self, title, "", filter)
        if filename:
            line_edit.setText(filename)

    def browse_folder(self, line_edit, title):
        folder = QFileDialog.getExistingDirectory(self, title)
        if folder:
            line_edit.setText(folder)

    def get_config(self):
        return {
            "detector_path": self.detector_path_edit.text(),
            "classifier_path": self.classifier_path_edit.text(),
            "cls_conf": self.cls_conf_spin.value(),
            "main_images_dir": self.main_images_dir_edit.text(),
            "main_json": self.main_json_edit.text(),
            "auto_json": self.auto_json_edit.text(),
            "font_path": self.current_config["font_path"],
            "thumbnail_cache": self.thumb_cache_check.isChecked(),
            "thumbnail_quality": self.thumb_quality_spin.value(),
            "async_image_loading": self.async_load_check.isChecked(),
            "auto_hide_panel": self.auto_hide_check.isChecked(),  # новая опция
        }