# ui/production_export_dialog.py
import os
import sys
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QComboBox, QCheckBox, QLineEdit, 
                             QFileDialog, QMessageBox, QGroupBox, QTextEdit, 
                             QProgressBar, QWidget)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont
from ui.theme import get_current_theme_style
from core.i18n import tr


class ExportWorker(QThread):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, str, str)

    def __init__(self, model_path, export_format, half, dynamic, simplify, imgsz, output_dir):
        super().__init__()
        self.model_path = model_path
        self.export_format = export_format
        self.half = half
        self.dynamic = dynamic
        self.simplify = simplify
        self.imgsz = imgsz
        self.output_dir = output_dir

    def run(self):
        try:
            from ultralytics import YOLO
            self.log_signal.emit(f"🚀 Загрузка модели: {self.model_path}")
            model = YOLO(self.model_path)

            format_code = self.export_format.lower()
            if format_code == "tensorrt":
                format_code = "engine"

            self.log_signal.emit(f"⚙️ Запуск экспорта в формат: {self.export_format.upper()} (imgsz={self.imgsz}, half={self.half}, dynamic={self.dynamic})...")
            
            export_kwargs = {
                "format": format_code,
                "imgsz": self.imgsz,
                "half": self.half,
                "dynamic": self.dynamic,
                "simplify": self.simplify
            }

            exported_path = model.export(**export_kwargs)
            self.log_signal.emit(f"✅ Экспорт успешно завершен!\nФайл: {exported_path}")
            self.finished_signal.emit(True, f"Модель успешно экспортирована в формат {self.export_format.upper()}", str(exported_path))
        except Exception as e:
            err_msg = str(e)
            self.log_signal.emit(f"❌ Ошибка экспорта: {err_msg}")
            self.finished_signal.emit(False, err_msg, "")


class ProductionExportDialog(QDialog):
    def __init__(self, parent=None, default_model_path=None):
        super().__init__(parent)
        self.default_model_path = default_model_path or ""
        self.exported_file_path = None
        self.worker = None

        self.setWindowTitle(tr("Экспорт модели в Production (ONNX / TensorRT / OpenVINO)"))
        self.setMinimumSize(680, 560)
        self.setStyleSheet(get_current_theme_style())

        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # 1. Выбор исходной модели
        src_group = QGroupBox(tr("Исходная модель"))
        src_layout = QHBoxLayout(src_group)
        self.model_path_edit = QLineEdit(self.default_model_path)
        self.model_path_edit.setPlaceholderText(tr("Путь к обученному файлу модели (.pt)..."))
        self.browse_model_btn = QPushButton(tr("Обзор..."))
        self.browse_model_btn.clicked.connect(self.browse_model)
        src_layout.addWidget(self.model_path_edit)
        src_layout.addWidget(self.browse_model_btn)
        layout.addWidget(src_group)

        # 2. Настройки экспорта
        opt_group = QGroupBox(tr("Параметры целевого формата"))
        opt_layout = QVBoxLayout(opt_group)

        fmt_layout = QHBoxLayout()
        fmt_label = QLabel(tr("Формат экспорта:"))
        fmt_label.setFixedWidth(140)
        self.format_combo = QComboBox()
        self.format_combo.addItems([
            "ONNX",
            "TensorRT",
            "OpenVINO",
            "TorchScript",
            "CoreML"
        ])
        fmt_layout.addWidget(fmt_label)
        fmt_layout.addWidget(self.format_combo)
        opt_layout.addLayout(fmt_layout)

        imgsz_layout = QHBoxLayout()
        imgsz_label = QLabel(tr("Размер изображения (imgsz):"))
        imgsz_label.setFixedWidth(140)
        self.imgsz_combo = QComboBox()
        self.imgsz_combo.addItems(["640", "1280", "320", "800", "1024"])
        self.imgsz_combo.setEditable(True)
        imgsz_layout.addWidget(imgsz_label)
        imgsz_layout.addWidget(self.imgsz_combo)
        opt_layout.addLayout(imgsz_layout)

        check_layout = QHBoxLayout()
        self.half_check = QCheckBox(tr("FP16 (Half precision — ускорение на GPU)"))
        self.half_check.setChecked(True)
        self.dynamic_check = QCheckBox(tr("Динамический размер батча (Dynamic shapes)"))
        self.simplify_check = QCheckBox(tr("Оптимизация графа (ONNX Simplify)"))
        self.simplify_check.setChecked(True)

        check_layout.addWidget(self.half_check)
        check_layout.addWidget(self.dynamic_check)
        check_layout.addWidget(self.simplify_check)
        opt_layout.addLayout(check_layout)

        layout.addWidget(opt_group)

        # 3. Терминал логов экспорта
        log_group = QGroupBox(tr("Процесс конвертации"))
        log_layout = QVBoxLayout(log_group)
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setFont(QFont("Consolas", 10))
        self.log_view.setStyleSheet("""
            QTextEdit {
                background-color: #121216;
                color: #22c55e;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 6px;
                padding: 6px;
            }
        """)
        log_layout.addWidget(self.log_view)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #1e1e24;
                border: none;
                border-radius: 3px;
            }
            QProgressBar::chunk {
                background-color: #4f46e5;
                border-radius: 3px;
            }
        """)
        log_layout.addWidget(self.progress_bar)
        layout.addWidget(log_group)

        # 4. Кнопки действий
        btn_layout = QHBoxLayout()
        self.export_btn = QPushButton(tr("Начать экспорт"))
        self.export_btn.setFixedHeight(34)
        self.export_btn.setStyleSheet("""
            QPushButton {
                background-color: #4f46e5;
                color: #ffffff;
                font-weight: bold;
                border-radius: 6px;
                padding: 0 16px;
            }
            QPushButton:hover {
                background-color: #4338ca;
            }
        """)
        self.export_btn.clicked.connect(self.start_export)

        self.close_btn = QPushButton(tr("Закрыть"))
        self.close_btn.setFixedHeight(34)
        self.close_btn.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(self.export_btn)
        btn_layout.addWidget(self.close_btn)
        layout.addLayout(btn_layout)

    def browse_model(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            tr("Выберите файл модели YOLO"),
            os.getcwd(),
            "YOLO Models (*.pt);;All Files (*.*)"
        )
        if file_path:
            self.model_path_edit.setText(file_path)

    def start_export(self):
        model_path = self.model_path_edit.text().strip()
        if not model_path or not os.path.exists(model_path):
            QMessageBox.warning(self, tr("Ошибка"), tr("Укажите существующий файл модели (.pt)"))
            return

        fmt = self.format_combo.currentText()
        try:
            imgsz = int(self.imgsz_combo.currentText())
        except ValueError:
            imgsz = 640

        self.export_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.log_view.clear()
        self.log_view.append(tr("Инициализация экспорта..."))

        self.worker = ExportWorker(
            model_path=model_path,
            export_format=fmt,
            half=self.half_check.isChecked(),
            dynamic=self.dynamic_check.isChecked(),
            simplify=self.simplify_check.isChecked(),
            imgsz=imgsz,
            output_dir=os.path.dirname(model_path)
        )
        self.worker.log_signal.connect(self.on_log)
        self.worker.finished_signal.connect(self.on_export_finished)
        self.worker.start()

    def on_log(self, text):
        self.log_view.append(text)
        sb = self.log_view.verticalScrollBar()
        sb.setValue(sb.maximum())

    def on_export_finished(self, success, msg, exported_path):
        self.export_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        if success:
            self.exported_file_path = exported_path
            QMessageBox.information(
                self,
                tr("Экспорт завершен"),
                f"{msg}\n\n{tr('Файл сохранен')}:\n{exported_path}"
            )
        else:
            QMessageBox.critical(
                self,
                tr("Ошибка экспорта"),
                f"{tr('Не удалось выполнить экспорт')}:\n{msg}"
            )
