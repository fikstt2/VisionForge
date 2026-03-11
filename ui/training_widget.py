# ui/training_widget.py
import os
import sys
import time
import contextlib
import io

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QComboBox, QLineEdit, QSpinBox, QCheckBox,
                             QPushButton, QFileDialog, QMessageBox, QTabWidget,
                             QTextEdit, QProgressBar, QFormLayout, QGroupBox,
                             QRadioButton, QDoubleSpinBox, QGridLayout)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QWaitCondition, QMutex
from PyQt5.QtGui import QFont
import matplotlib
matplotlib.use('Qt5Agg')
import matplotlib.pyplot as plt
plt.style.use('dark_background')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

project_root = os.path.dirname(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    torch = None

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    psutil = None

MODEL_FAMILIES = {
    'detect': {
        'YOLOv8': ['n', 's', 'm', 'l', 'x'],
        'YOLOv9': ['t', 's', 'm', 'c', 'e'],
        'YOLOv10': ['n', 'm', 'l', 'x'],
        'YOLOv11': ['n', 's', 'm', 'l', 'x'],
        'YOLOv26': ['n', 's', 'm', 'l', 'x'],
        'Custom': ['custom']
    },
    'classify': {
        'YOLOv8-cls': ['n', 's', 'm', 'l', 'x'],
        'YOLOv9-cls': ['t', 's', 'm', 'c', 'e'],
        'YOLOv10-cls': ['n', 'm', 'l', 'x'],
        'YOLOv11-cls': ['n', 's', 'm', 'l', 'x'],
        'YOLOv26-cls': ['n', 's', 'm', 'l', 'x'],
        'Custom': ['custom']
    }
}

def estimate_vram_detection(family, size, imgsz, batch):
    base_mult = {
        'YOLOv8': {'n': 1.0, 's': 1.8, 'm': 3.0, 'l': 5.0, 'x': 8.0},
        'YOLOv9': {'t': 1.2, 's': 2.0, 'm': 3.5, 'c': 6.0, 'e': 10.0},
        'YOLOv10': {'n': 1.1, 'm': 3.2, 'l': 5.5, 'x': 9.0},
        'YOLOv11': {'n': 1.0, 's': 1.8, 'm': 3.0, 'l': 5.0, 'x': 8.0},
        'YOLOv26': {'n': 1.0, 's': 1.8, 'm': 3.0, 'l': 5.0, 'x': 8.0},
    }
    mult = base_mult.get(family, {}).get(size, 1.0)
    scale = (imgsz / 640) ** 2
    vram_gb = mult * batch * scale * 0.1
    return max(1.0, round(vram_gb, 1))

def estimate_vram_classification(family, size, imgsz, batch):
    base_mult = {
        'YOLOv8-cls': {'n': 0.5, 's': 0.8, 'm': 1.2, 'l': 2.0, 'x': 3.0},
        'YOLOv9-cls': {'t': 0.6, 's': 0.9, 'm': 1.5, 'c': 2.5, 'e': 4.0},
        'YOLOv10-cls': {'n': 0.5, 'm': 1.2, 'l': 2.0, 'x': 3.0},
        'YOLOv11-cls': {'n': 0.5, 's': 0.8, 'm': 1.2, 'l': 2.0, 'x': 3.0},
        'YOLOv26-cls': {'n': 0.5, 's': 0.8, 'm': 1.2, 'l': 2.0, 'x': 3.0},
    }
    mult = base_mult.get(family, {}).get(size, 0.5)
    scale = (imgsz / 224) ** 2
    vram_gb = mult * batch * scale * 0.05
    return max(0.5, round(vram_gb, 1))

class StreamRedirector:
    def __init__(self, signal):
        self.signal = signal
        self.buffer = ""

    def write(self, text):
        self.buffer += text
        if text.endswith('\n'):
            self.signal.emit(self.buffer.rstrip())
            self.buffer = ""

    def flush(self):
        if self.buffer:
            self.signal.emit(self.buffer.rstrip())
            self.buffer = ""

class TrainWorker(QThread):
    log_signal = pyqtSignal(str)
    epoch_signal = pyqtSignal(int, dict)
    finished_signal = pyqtSignal(bool)
    paused_signal = pyqtSignal()

    def __init__(self, task_type, model_name, data_yaml, params):
        super().__init__()
        self.task_type = task_type
        self.model_name = model_name
        self.data_yaml = data_yaml
        self.params = params
        self._is_running = True
        self._paused = False
        self.pause_condition = QWaitCondition()
        self.pause_mutex = QMutex()

    def run(self):
        try:
            from ultralytics import YOLO
            import sys

            old_stdout = sys.stdout
            old_stderr = sys.stderr
            redirector = StreamRedirector(self.log_signal)
            sys.stdout = redirector
            sys.stderr = redirector

            self.log_signal.emit(f"Загрузка модели {self.model_name}...")
            model = YOLO(self.model_name)
            self.log_signal.emit("Модель загружена. Начинаем обучение...")

            model.add_callback('on_train_epoch_end', self.on_epoch_end)
            model.add_callback('on_train_end', self.on_train_end)

            if self.task_type == 'classify':
                model.train(data=self.data_yaml, task='classify', **self.params, verbose=True)
            else:
                model.train(data=self.data_yaml, **self.params, verbose=True)
            self.finished_signal.emit(True)
        except Exception as e:
            self.log_signal.emit(f"Ошибка: {str(e)}")
            self.finished_signal.emit(False)
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

    def on_epoch_end(self, trainer):
        if not self._is_running:
            trainer.stop()
            return
        self.pause_mutex.lock()
        if self._paused:
            self.paused_signal.emit()
            self.pause_condition.wait(self.pause_mutex)
        self.pause_mutex.unlock()

        epoch = trainer.epoch
        metrics = trainer.metrics.copy() if trainer.metrics else {}
        self.epoch_signal.emit(epoch, metrics)

    def on_train_end(self, trainer):
        self.log_signal.emit("Обучение завершено.")

    def stop(self):
        self._is_running = False
        self.resume()

    def pause(self):
        self.pause_mutex.lock()
        self._paused = True
        self.pause_mutex.unlock()

    def resume(self):
        self.pause_mutex.lock()
        self._paused = False
        self.pause_condition.wakeAll()
        self.pause_mutex.unlock()

class TrainingWidget(QWidget):
    switch_to_annotation = pyqtSignal()

    def __init__(self, detector=None, classifier=None):
        super().__init__()
        self.detector = detector
        self.classifier = classifier
        self.epochs_data = []
        self.loss_data = {}
        self.map_data = []
        self.map95_data = []
        self.precision_data = []
        self.recall_data = []
        self.acc_data = []
        self.worker = None
        self.start_time = 0
        self.last_epoch_time = 0
        self.avg_epoch_time = 0
        self.init_ui()
        self.update_vram_estimate()

    def init_ui(self):
        main_layout = QVBoxLayout(self)

        # Верхняя панель с кнопкой возврата
        top_layout = QHBoxLayout()
        self.back_btn = QPushButton("← Вернуться к разметке")
        self.back_btn.clicked.connect(self.switch_to_annotation)
        top_layout.addWidget(self.back_btn)
        top_layout.addStretch()
        main_layout.addLayout(top_layout)

        tabs = QTabWidget()
        main_layout.addWidget(tabs)

        # --- Вкладка "Управление" ---
        control_tab = QWidget()
        control_layout = QVBoxLayout(control_tab)
        tabs.addTab(control_tab, "Управление")

        task_group = QGroupBox("Тип задачи")
        task_layout = QHBoxLayout()
        self.task_detect = QRadioButton("Детекция")
        self.task_classify = QRadioButton("Классификация")
        self.task_detect.setChecked(True)
        self.task_detect.toggled.connect(self.on_task_changed)
        self.task_detect.toggled.connect(self.update_vram_estimate)
        self.task_classify.toggled.connect(self.update_vram_estimate)
        task_layout.addWidget(self.task_detect)
        task_layout.addWidget(self.task_classify)
        task_layout.addStretch()
        task_group.setLayout(task_layout)
        control_layout.addWidget(task_group)

        model_group = QGroupBox("Выбор модели")
        model_layout = QFormLayout()

        self.family_combo = QComboBox()
        self.size_combo = QComboBox()
        self.custom_model_edit = QLineEdit()
        self.custom_model_edit.setPlaceholderText("Путь к файлу модели .pt")
        self.custom_model_edit.setEnabled(False)
        custom_browse = QPushButton("Обзор...")
        custom_browse.clicked.connect(self.browse_custom_model)
        custom_layout = QHBoxLayout()
        custom_layout.addWidget(self.custom_model_edit)
        custom_layout.addWidget(custom_browse)

        model_layout.addRow("Семейство:", self.family_combo)
        model_layout.addRow("Размер:", self.size_combo)
        model_layout.addRow("Custom модель:", custom_layout)

        model_group.setLayout(model_layout)
        control_layout.addWidget(model_group)

        self.update_family_list('detect')
        self.family_combo.currentTextChanged.connect(self.update_size_list)
        self.family_combo.currentTextChanged.connect(self.update_vram_estimate)
        self.size_combo.currentTextChanged.connect(self.update_vram_estimate)

        form_group = QGroupBox("Параметры обучения")
        form_layout = QFormLayout()

        self.data_edit = QLineEdit()
        self.data_edit.setPlaceholderText("Путь к data.yaml (или папке для классификации)")
        data_browse = QPushButton("Обзор...")
        data_browse.clicked.connect(self.browse_data)
        data_layout = QHBoxLayout()
        data_layout.addWidget(self.data_edit)
        data_layout.addWidget(data_browse)
        form_layout.addRow("Датасет:", data_layout)

        self.epochs_spin = QSpinBox()
        self.epochs_spin.setRange(1, 1000)
        self.epochs_spin.setValue(100)
        self.epochs_spin.valueChanged.connect(self.update_vram_estimate)
        form_layout.addRow("Эпохи:", self.epochs_spin)

        self.batch_spin = QSpinBox()
        self.batch_spin.setRange(1, 256)
        self.batch_spin.setValue(16)
        self.batch_spin.valueChanged.connect(self.update_vram_estimate)
        form_layout.addRow("Batch:", self.batch_spin)

        self.imgsz_spin = QSpinBox()
        self.imgsz_spin.setRange(32, 1280)
        self.imgsz_spin.setValue(640)
        self.imgsz_spin.valueChanged.connect(self.update_vram_estimate)
        form_layout.addRow("Image size:", self.imgsz_spin)

        self.device_combo = QComboBox()
        self.device_combo.setEditable(True)
        self.device_combo.setInsertPolicy(QComboBox.NoInsert)
        self.populate_device_list()
        self.device_combo.currentTextChanged.connect(self.update_vram_estimate)
        form_layout.addRow("Device:", self.device_combo)

        self.workers_spin = QSpinBox()
        self.workers_spin.setRange(0, 16)
        if getattr(sys, 'frozen', False):
            self.workers_spin.setValue(0)
            self.workers_spin.setEnabled(False)
            self.workers_spin.setToolTip("В скомпилированной версии workers должен быть 0")
        else:
            self.workers_spin.setValue(8)
        form_layout.addRow("Workers:", self.workers_spin)

        self.patience_spin = QSpinBox()
        self.patience_spin.setRange(0, 1000)
        self.patience_spin.setValue(50)
        form_layout.addRow("Patience:", self.patience_spin)

        self.project_edit = QLineEdit()
        self.project_edit.setText("runs/train")
        form_layout.addRow("Project:", self.project_edit)

        self.name_edit = QLineEdit()
        self.name_edit.setText("exp")
        form_layout.addRow("Name:", self.name_edit)

        self.exist_ok_check = QCheckBox()
        self.exist_ok_check.setChecked(False)
        form_layout.addRow("Exist OK:", self.exist_ok_check)

        form_group.setLayout(form_layout)
        control_layout.addWidget(form_group)

        self.vram_label = QLabel("")
        self.vram_label.setWordWrap(True)
        control_layout.addWidget(self.vram_label)

        # --- Вкладка "Аугментация" ---
        aug_tab = QWidget()
        aug_layout = QVBoxLayout(aug_tab)

        aug_group = QGroupBox("Параметры аугментации данных")
        aug_grid = QGridLayout()

        # Список параметров: (имя, тип, минимум, максимум, шаг, значение по умолчанию, подсказка)
        aug_params = [
            ("hsv_h", "float", 0.0, 1.0, 0.01, 0.015, "Изменение оттенка HSV"),
            ("hsv_s", "float", 0.0, 1.0, 0.01, 0.7, "Изменение насыщенности HSV"),
            ("hsv_v", "float", 0.0, 1.0, 0.01, 0.4, "Изменение яркости HSV"),
            ("degrees", "float", 0.0, 180.0, 1.0, 0.0, "Поворот в градусах"),
            ("translate", "float", 0.0, 1.0, 0.01, 0.1, "Сдвиг (доля размера)"),
            ("scale", "float", 0.0, 10.0, 0.1, 0.5, "Масштабирование"),
            ("shear", "float", 0.0, 180.0, 1.0, 0.0, "Сдвиг в градусах"),
            ("perspective", "float", 0.0, 1.0, 0.01, 0.0, "Перспективное искажение"),
            ("flipud", "float", 0.0, 1.0, 0.01, 0.0, "Вероятность вертикального отражения"),
            ("fliplr", "float", 0.0, 1.0, 0.01, 0.5, "Вероятность горизонтального отражения"),
            ("mosaic", "float", 0.0, 1.0, 0.01, 1.0, "Вероятность мозаики"),
            ("mixup", "float", 0.0, 1.0, 0.01, 0.0, "Вероятность MixUp"),
            ("copy_paste", "float", 0.0, 1.0, 0.01, 0.0, "Вероятность Copy-Paste"),
        ]

        self.aug_widgets = {}
        row = 0
        col = 0
        for name, typ, minv, maxv, step, default, tooltip in aug_params:
            label = QLabel(name)
            label.setToolTip(tooltip)
            spin = QDoubleSpinBox()
            spin.setRange(minv, maxv)
            spin.setSingleStep(step)
            spin.setValue(default)
            spin.setToolTip(tooltip)
            spin.setDecimals(3)
            self.aug_widgets[name] = spin
            aug_grid.addWidget(label, row, col*2)
            aug_grid.addWidget(spin, row, col*2+1)
            row += 1
            if row >= 7:
                row = 0
                col = 1

        aug_group.setLayout(aug_grid)
        aug_layout.addWidget(aug_group)

        # Кнопка сброса к значениям по умолчанию
        reset_btn = QPushButton("Сбросить к значениям по умолчанию")
        reset_btn.clicked.connect(self.reset_augmentation)
        aug_layout.addWidget(reset_btn)

        aug_layout.addStretch()
        tabs.addTab(aug_tab, "Аугментация")

        # --- Кнопки управления обучением ---
        btn_layout = QHBoxLayout()
        self.start_btn = QPushButton("Старт")
        self.start_btn.clicked.connect(self.start_training)
        self.pause_btn = QPushButton("Пауза")
        self.pause_btn.setEnabled(False)
        self.pause_btn.clicked.connect(self.toggle_pause)
        self.stop_btn = QPushButton("Стоп")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_training)
        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.pause_btn)
        btn_layout.addWidget(self.stop_btn)
        btn_layout.addStretch()
        control_layout.addLayout(btn_layout)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        control_layout.addWidget(self.progress)

        self.time_label = QLabel("Осталось: --:--:--")
        self.time_label.setAlignment(Qt.AlignCenter)
        control_layout.addWidget(self.time_label)

        # --- Вкладка графиков ---
        plot_tab = QWidget()
        plot_layout = QVBoxLayout(plot_tab)
        tabs.addTab(plot_tab, "Графики")

        self.figure = Figure(figsize=(8, 6))
        self.canvas = FigureCanvas(self.figure)
        plot_layout.addWidget(self.canvas)

        self.ax1 = self.figure.add_subplot(211)
        self.ax2 = self.figure.add_subplot(212)
        self.ax1.set_xlabel('Epoch')
        self.ax2.set_xlabel('Epoch')
        self.figure.tight_layout()

        # --- Вкладка логов ---
        log_tab = QWidget()
        log_layout = QVBoxLayout(log_tab)
        tabs.addTab(log_tab, "Логи")

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Courier New", 10))
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #00ff00;
                font-family: 'Courier New', monospace;
                font-size: 10pt;
                border: 1px solid #3c3c3c;
            }
        """)
        log_layout.addWidget(self.log_text)

    def reset_augmentation(self):
        """Сбрасывает параметры аугментации к значениям по умолчанию."""
        defaults = {
            "hsv_h": 0.015,
            "hsv_s": 0.7,
            "hsv_v": 0.4,
            "degrees": 0.0,
            "translate": 0.1,
            "scale": 0.5,
            "shear": 0.0,
            "perspective": 0.0,
            "flipud": 0.0,
            "fliplr": 0.5,
            "mosaic": 1.0,
            "mixup": 0.0,
            "copy_paste": 0.0,
        }
        for name, widget in self.aug_widgets.items():
            if name in defaults:
                widget.setValue(defaults[name])

    def populate_device_list(self):
        items = ["cpu"]
        if TORCH_AVAILABLE and torch.cuda.is_available():
            for i in range(torch.cuda.device_count()):
                device_name = torch.cuda.get_device_name(i)
                items.append(f"cuda:{i} ({device_name})")
        if TORCH_AVAILABLE and hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            items.append("mps")
        self.device_combo.clear()
        self.device_combo.addItems(items)
        self.device_combo.setCurrentText("cpu")

    def get_device_string(self):
        text = self.device_combo.currentText()
        if '(' in text:
            text = text.split('(')[0].strip()
        return text

    def get_available_memory(self):
        device = self.get_device_string()
        if device.startswith('cuda'):
            if TORCH_AVAILABLE and torch.cuda.is_available():
                try:
                    idx = 0
                    if ':' in device:
                        idx = int(device.split(':')[1])
                    free, total = torch.cuda.mem_get_info(idx)
                    return free / (1024**3)
                except:
                    return None
        elif device == 'mps':
            return None
        else:
            if PSUTIL_AVAILABLE:
                mem = psutil.virtual_memory()
                return mem.available / (1024**3)
            else:
                return None

    def update_vram_estimate(self):
        try:
            family = self.family_combo.currentText()
            size = self.size_combo.currentText()
            imgsz = self.imgsz_spin.value()
            batch = self.batch_spin.value()
            task = 'detect' if self.task_detect.isChecked() else 'classify'
            device = self.get_device_string()

            if family == 'Custom' or not size:
                self.vram_label.setText("")
                return

            if task == 'detect':
                vram_needed = estimate_vram_detection(family, size, imgsz, batch)
            else:
                vram_needed = estimate_vram_classification(family, size, imgsz, batch)

            available = self.get_available_memory()
            if available is not None:
                if vram_needed > available * 0.9:
                    color = "red"
                    msg = (f"⚠️ Оценочное потребление {vram_needed:.1f} GB превышает 90% "
                           f"доступной памяти ({available:.1f} GB). Возможен Out of Memory!")
                elif vram_needed > available * 0.7:
                    color = "orange"
                    msg = (f"⚠️ Оценочное потребление {vram_needed:.1f} GB близко к доступной "
                           f"памяти ({available:.1f} GB). Риск нехватки.")
                else:
                    color = "green"
                    msg = (f"✅ Оценочное потребление {vram_needed:.1f} GB. Доступно "
                           f"{available:.1f} GB. Должно хватить.")
            else:
                msg = (f"⚠️ Приблизительное потребление памяти: ~{vram_needed} GB. "
                       "Не удалось определить доступную память.")
                color = "orange"

            self.vram_label.setStyleSheet(f"color: {color}; font-weight: bold;")
            self.vram_label.setText(msg)
        except Exception:
            self.vram_label.setText("")

    def update_family_list(self, task):
        self.family_combo.blockSignals(True)
        self.family_combo.clear()
        families = MODEL_FAMILIES[task].keys()
        self.family_combo.addItems(families)
        self.family_combo.blockSignals(False)
        self.update_size_list()

    def update_size_list(self):
        task = 'detect' if self.task_detect.isChecked() else 'classify'
        family = self.family_combo.currentText()
        if not family:
            return
        sizes = MODEL_FAMILIES[task].get(family, [])
        self.size_combo.blockSignals(True)
        self.size_combo.clear()
        self.size_combo.addItems(sizes)
        self.size_combo.blockSignals(False)
        self.custom_model_edit.setEnabled(family == 'Custom')

    def on_task_changed(self):
        task = 'detect' if self.task_detect.isChecked() else 'classify'
        self.update_family_list(task)
        self.update_size_list()
        self.update_vram_estimate()

    def browse_custom_model(self):
        path, _ = QFileDialog.getOpenFileName(self, "Выберите файл модели", "", "Model files (*.pt)")
        if path:
            self.custom_model_edit.setText(path)

    def browse_data(self):
        if self.task_detect.isChecked():
            path, _ = QFileDialog.getOpenFileName(self, "Выберите data.yaml", "", "YAML files (*.yaml)")
        else:
            path = QFileDialog.getExistingDirectory(self, "Выберите корневую папку с данными (train/val)")
        if path:
            self.data_edit.setText(path)

    def get_model_path(self):
        family = self.family_combo.currentText()
        if family == 'Custom':
            return self.custom_model_edit.text()
        size = self.size_combo.currentText()
        if self.task_detect.isChecked():
            if family.startswith('YOLOv8'):
                return f"yolov8{size}.pt"
            elif family.startswith('YOLOv9'):
                return f"yolov9{size}.pt"
            elif family.startswith('YOLOv10'):
                return f"yolov10{size}.pt"
            elif family.startswith('YOLOv11'):
                return f"yolo11{size}.pt"
            elif family.startswith('YOLOv26'):
                return f"yolo26{size}.pt"
            else:
                return f"yolov8{size}.pt"
        else:
            if family.startswith('YOLOv8'):
                return f"yolov8{size}-cls.pt"
            elif family.startswith('YOLOv9'):
                return f"yolov9{size}-cls.pt"
            elif family.startswith('YOLOv10'):
                return f"yolov10{size}-cls.pt"
            elif family.startswith('YOLOv11'):
                return f"yolo11{size}-cls.pt"
            elif family.startswith('YOLOv26'):
                return f"yolo26{size}-cls.pt"
            else:
                return f"yolov8{size}-cls.pt"

    def get_params(self):
        params = {
            'epochs': self.epochs_spin.value(),
            'batch': self.batch_spin.value(),
            'imgsz': self.imgsz_spin.value(),
            'workers': self.workers_spin.value(),
            'patience': self.patience_spin.value(),
            'project': self.project_edit.text(),
            'name': self.name_edit.text(),
            'exist_ok': self.exist_ok_check.isChecked(),
            'device': self.get_device_string()
        }
        # Добавляем параметры аугментации
        for name, widget in self.aug_widgets.items():
            params[name] = widget.value()
        return params

    def start_training(self):
        task = 'detect' if self.task_detect.isChecked() else 'classify'
        model_path = self.get_model_path()
        data_path = self.data_edit.text()
        if self.family_combo.currentText() == 'Custom':
            if not os.path.exists(model_path):
                QMessageBox.warning(self, "Ошибка", f"Файл модели не найден: {model_path}")
                return
        if not os.path.exists(data_path):
            QMessageBox.warning(self, "Ошибка", f"Датасет не найден: {data_path}")
            return

        params = self.get_params()

        self.epochs_data.clear()
        self.loss_data.clear()
        self.map_data.clear()
        self.map95_data.clear()
        self.precision_data.clear()
        self.recall_data.clear()
        self.acc_data.clear()
        self.update_plot()
        self.progress.setValue(0)
        self.time_label.setText("Осталось: --:--:--")
        self.start_time = time.time()
        self.last_epoch_time = 0
        self.avg_epoch_time = 0

        self.worker = TrainWorker(task, model_path, data_path, params)
        self.worker.log_signal.connect(self.add_log)
        self.worker.epoch_signal.connect(self.on_epoch_update)
        self.worker.finished_signal.connect(self.on_training_finished)
        self.worker.paused_signal.connect(self.on_paused)
        self.worker.start()

        self.start_btn.setEnabled(False)
        self.pause_btn.setEnabled(True)
        self.pause_btn.setText("Пауза")
        self.stop_btn.setEnabled(True)
        self.add_log("Обучение запущено...")

    def toggle_pause(self):
        if self.worker is None:
            return
        if self.pause_btn.text() == "Пауза":
            self.worker.pause()
            self.pause_btn.setText("Продолжить")
            self.add_log("Обучение приостановлено.")
        else:
            self.worker.resume()
            self.pause_btn.setText("Пауза")
            self.add_log("Обучение возобновлено.")

    def stop_training(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.add_log("Остановка обучения...")
            if not self.worker.wait(2000):
                self.worker.terminate()
                self.worker.wait()
            self.stop_btn.setEnabled(False)
            self.pause_btn.setEnabled(False)
            self.start_btn.setEnabled(True)
            self.add_log("Обучение остановлено.")
            self.time_label.setText("Осталось: --:--:--")

    def on_paused(self):
        pass

    def on_epoch_update(self, epoch, metrics):
        total = self.epochs_spin.value()
        self.progress.setValue(int(epoch / total * 100))

        current_time = time.time()
        if self.last_epoch_time > 0:
            epoch_duration = current_time - self.last_epoch_time
            if self.avg_epoch_time == 0:
                self.avg_epoch_time = epoch_duration
            else:
                self.avg_epoch_time = 0.9 * self.avg_epoch_time + 0.1 * epoch_duration
        self.last_epoch_time = current_time

        remaining_epochs = total - epoch
        if self.avg_epoch_time > 0:
            remaining_seconds = int(remaining_epochs * self.avg_epoch_time)
            hours = remaining_seconds // 3600
            minutes = (remaining_seconds % 3600) // 60
            seconds = remaining_seconds % 60
            self.time_label.setText(f"Осталось: {hours:02d}:{minutes:02d}:{seconds:02d}")
        else:
            self.time_label.setText("Осталось: --:--:--")

        self.epochs_data.append(epoch)

        if self.task_detect.isChecked():
            # Потери
            box_loss = metrics.get('train/box_loss', metrics.get('box_loss', 0))
            cls_loss = metrics.get('train/cls_loss', metrics.get('cls_loss', 0))
            dfl_loss = metrics.get('train/dfl_loss', metrics.get('dfl_loss', 0))
            self.loss_data.setdefault('box_loss', []).append(box_loss)
            self.loss_data.setdefault('cls_loss', []).append(cls_loss)
            self.loss_data.setdefault('dfl_loss', []).append(dfl_loss)

            # mAP
            map50 = metrics.get('metrics/mAP50(B)', metrics.get('mAP50', metrics.get('map50', 0)))
            map95 = metrics.get('metrics/mAP50-95(B)', metrics.get('mAP50-95', metrics.get('map50-95', 0)))
            self.map_data.append(map50)
            self.map95_data.append(map95)

            # Precision, Recall (если есть)
            prec = metrics.get('metrics/precision(B)', metrics.get('precision', 0))
            rec = metrics.get('metrics/recall(B)', metrics.get('recall', 0))
            self.precision_data.append(prec)
            self.recall_data.append(rec)

            loss_msg = (f"Эпоха {epoch}: box={box_loss:.4f}, cls={cls_loss:.4f}, dfl={dfl_loss:.4f}, "
                        f"mAP50={map50:.4f}, mAP95={map95:.4f}, P={prec:.4f}, R={rec:.4f}")
        else:
            loss = metrics.get('loss', 0)
            acc = metrics.get('accuracy', 0)
            self.loss_data.setdefault('loss', []).append(loss)
            self.acc_data.append(acc)
            loss_msg = f"Эпоха {epoch}: loss={loss:.4f}, acc={acc:.4f}"

        self.add_log(loss_msg)
        self.update_plot()

    def update_plot(self):
        self.ax1.clear()
        self.ax2.clear()
        if self.epochs_data:
            if self.task_detect.isChecked():
                # Потери
                if 'box_loss' in self.loss_data:
                    self.ax1.plot(self.epochs_data, self.loss_data['box_loss'], label='box_loss')
                if 'cls_loss' in self.loss_data:
                    self.ax1.plot(self.epochs_data, self.loss_data['cls_loss'], label='cls_loss')
                if 'dfl_loss' in self.loss_data:
                    self.ax1.plot(self.epochs_data, self.loss_data['dfl_loss'], label='dfl_loss')
                self.ax1.legend()
                self.ax1.set_ylabel('Loss')
                self.ax1.set_title('Loss')

                # mAP и точность/полнота
                if self.map_data:
                    self.ax2.plot(self.epochs_data, self.map_data, label='mAP50', color='green')
                if self.map95_data and any(self.map95_data):
                    self.ax2.plot(self.epochs_data, self.map95_data, label='mAP50-95', color='blue')
                if self.precision_data and any(self.precision_data):
                    self.ax2.plot(self.epochs_data, self.precision_data, label='Precision', color='orange')
                if self.recall_data and any(self.recall_data):
                    self.ax2.plot(self.epochs_data, self.recall_data, label='Recall', color='red')
                self.ax2.legend()
                self.ax2.set_ylabel('Metrics')
                self.ax2.set_title('Metrics')
            else:
                if self.loss_data.get('loss'):
                    self.ax1.plot(self.epochs_data, self.loss_data['loss'], label='loss', color='red')
                    self.ax1.legend()
                    self.ax1.set_ylabel('Loss')
                    self.ax1.set_title('Loss')
                if self.acc_data:
                    self.ax2.plot(self.epochs_data, self.acc_data, label='accuracy', color='blue')
                    self.ax2.legend()
                    self.ax2.set_ylabel('Accuracy')
                    self.ax2.set_title('Accuracy')
        self.ax1.set_xlabel('Epoch')
        self.ax2.set_xlabel('Epoch')
        self.figure.tight_layout()
        self.canvas.draw()

    def on_training_finished(self, success):
        self.start_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        self.pause_btn.setText("Пауза")
        if success:
            self.add_log("Обучение успешно завершено.")
        else:
            self.add_log("Обучение завершено с ошибкой.")
        self.time_label.setText("Осталось: --:--:--")

    def add_log(self, msg):
        self.log_text.append(msg)
        self.log_text.moveCursor(self.log_text.textCursor().End)