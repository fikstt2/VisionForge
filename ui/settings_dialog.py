# ui/settings_dialog.py
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout,
                             QLineEdit, QPushButton, QFileDialog, QDoubleSpinBox,
                             QFormLayout, QDialogButtonBox, QTabWidget,
                             QCheckBox, QSpinBox, QWidget, QComboBox, QMessageBox)
from ui.theme import THEMES, get_current_theme_style
import config
from core.i18n import tr
import os

class SettingsDialog(QDialog):
    settings_changed = pyqtSignal()

    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.project = main_window.project
        self.setWindowTitle(tr("Настройки"))
        self.setModal(True)
        self.resize(600, 500)
        self.setStyleSheet(get_current_theme_style())

        self.current_config = config.load_config()
        layout = QVBoxLayout(self)
        tabs = QTabWidget()
        layout.addWidget(tabs)

        # ===== Вкладка "Проект" =====
        project_tab = QWidget()
        project_layout = QFormLayout(project_tab)
        
        self.images_path_edit = QLineEdit()
        if self.project:
            self.images_path_edit.setText(self.project.images_dir)
        else:
            self.images_path_edit.setPlaceholderText(tr("Проект не открыт"))
            self.images_path_edit.setEnabled(False)
            
        proj_browse = QPushButton(tr("Обзор..."))
        proj_browse.clicked.connect(self.browse_images_dir)
        proj_layout = QHBoxLayout()
        proj_layout.addWidget(self.images_path_edit)
        proj_layout.addWidget(proj_browse)
        project_layout.addRow(tr("Папка с изображениями:"), proj_layout)
        tabs.addTab(project_tab, tr("Проект"))

        # ===== Вкладка "Модели" =====
        model_tab = QWidget()
        model_layout = QFormLayout(model_tab)

        self.detector_path_edit = QLineEdit()
        self.detector_path_edit.setText(self.current_config.get("detector_path", ""))
        detector_browse = QPushButton(tr("Обзор..."))
        detector_browse.clicked.connect(lambda: self.browse_file(self.detector_path_edit, tr("Выберите файл детектора (*.pt)")))
        detector_layout = QHBoxLayout()
        detector_layout.addWidget(self.detector_path_edit)
        detector_layout.addWidget(detector_browse)
        model_layout.addRow(tr("Путь к детектору (.pt):"), detector_layout)

        self.classifier_path_edit = QLineEdit()
        self.classifier_path_edit.setText(self.current_config.get("classifier_path", ""))
        classifier_browse = QPushButton(tr("Обзор..."))
        classifier_browse.clicked.connect(lambda: self.browse_file(self.classifier_path_edit, tr("Выберите файл классификатора (*.pt)")))
        classifier_layout = QHBoxLayout()
        classifier_layout.addWidget(self.classifier_path_edit)
        classifier_layout.addWidget(classifier_browse)
        model_layout.addRow(tr("Путь к классификатору (.pt):"), classifier_layout)

        self.cls_conf_spin = QDoubleSpinBox()
        self.cls_conf_spin.setRange(0.0, 1.0)
        self.cls_conf_spin.setSingleStep(0.05)
        self.cls_conf_spin.setValue(self.current_config.get("cls_conf", 0.5))
        model_layout.addRow(tr("Confidence:"), self.cls_conf_spin)

        tabs.addTab(model_tab, tr("Модели"))

        # ===== Вкладка "Производительность" =====
        perf_tab = QWidget()
        perf_layout = QFormLayout(perf_tab)

        self.thumb_cache_check = QCheckBox(tr("Кэш миниатюр:"))
        self.thumb_cache_check.setChecked(self.current_config.get("thumbnail_cache", True))

        self.thumb_quality_spin = QSpinBox()
        self.thumb_quality_spin.setRange(1, 100)
        self.thumb_quality_spin.setValue(self.current_config.get("thumbnail_quality", 70))

        self.async_load_check = QCheckBox(tr("Асинхронная загрузка (экспериментально)"))
        self.async_load_check.setChecked(self.current_config.get("async_image_loading", False))

        perf_layout.addRow(self.thumb_cache_check)
        perf_layout.addRow(tr("Качество миниатюр:"), self.thumb_quality_spin)
        perf_layout.addRow(self.async_load_check)

        tabs.addTab(perf_tab, tr("Производительность"))

        # ===== Вкладка "Интерфейс" =====
        ui_tab = QWidget()
        ui_layout = QFormLayout(ui_tab)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(list(THEMES.keys()))
        self.theme_combo.setCurrentText(self.current_config.get("theme", tr("Тёмная")))
        ui_layout.addRow(tr("Тема:"), self.theme_combo)

        self.language_combo = QComboBox()
        self.language_combo.addItem(tr("Русский"), "ru")
        self.language_combo.addItem(tr("English"), "en")
        current_lang = self.current_config.get("language", "ru")
        idx = self.language_combo.findData(current_lang)
        if idx >= 0:
            self.language_combo.setCurrentIndex(idx)
        ui_layout.addRow(tr("Язык:"), self.language_combo)

        self.auto_hide_check = QCheckBox(tr("Автоскрытие панели:"))
        self.auto_hide_check.setChecked(self.current_config.get("auto_hide_panel", False))
        ui_layout.addRow(self.auto_hide_check)

        tabs.addTab(ui_tab, tr("Интерфейс"))

        # Кнопки OK/Cancel
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept_settings)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def browse_images_dir(self):
        folder = QFileDialog.getExistingDirectory(self, tr("Выберите папку с изображениями"))
        if folder:
            self.images_path_edit.setText(os.path.normpath(folder))

    def accept_settings(self):
        # 1. Если проект открыт, обновляем его путь и СРАЗУ сохраняем файл
        if self.project:
            new_path = self.images_path_edit.text()
            if os.path.exists(new_path): # Проверка на всякий случай
                self.project.images_dir = new_path
                self.project.save()
            else:
                QMessageBox.warning(self, tr("Ошибка"), tr("Указанный путь не существует!"))
                return # Прерываем, чтобы не сохранять битый путь
            
        # 2. Сохраняем глобальный конфиг
        new_cfg = self.get_config()
        config.save_config(new_cfg)

        self.settings_changed.emit()
        self.accept()
        
    def browse_file(self, line_edit, title, filter="*.pt *.pth"):
        filename, _ = QFileDialog.getOpenFileName(self, title, "", filter)
        if filename:
            line_edit.setText(filename)

    def get_config(self):
        return {
            "detector_path": self.detector_path_edit.text(),
            "classifier_path": self.classifier_path_edit.text(),
            "cls_conf": self.cls_conf_spin.value(),
            "font_path": self.current_config.get("font_path", ""),
            "thumbnail_cache": self.thumb_cache_check.isChecked(),
            "thumbnail_quality": self.thumb_quality_spin.value(),
            "async_image_loading": self.async_load_check.isChecked(),
            "auto_hide_panel": self.auto_hide_check.isChecked(),
            "theme": self.theme_combo.currentText(),
            "language": self.language_combo.currentData(),
            "recent_projects": self.current_config.get("recent_projects", [])
        }