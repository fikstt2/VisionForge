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
from core.i18n import tr

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
    },
    'segment': {
        'YOLOv8-seg': ['n', 's', 'm', 'l', 'x'],
        'YOLOv9-seg': ['t', 's', 'm', 'c', 'e'],
        'YOLOv10-seg': ['n', 'm', 'l', 'x'],
        'YOLOv11-seg': ['n', 's', 'm', 'l', 'x'],
        'YOLOv26-seg': ['n', 's', 'm', 'l', 'x'],
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

def estimate_vram_segmentation(family, size, imgsz, batch):
    """Оценка VRAM для сегментационных моделей (~15-25% больше детекции)."""
    base_mult = {
        'YOLOv8-seg': {'n': 1.2, 's': 2.1, 'm': 3.5, 'l': 5.8, 'x': 9.2},
        'YOLOv9-seg': {'t': 1.4, 's': 2.3, 'm': 4.0, 'c': 6.8, 'e': 11.5},
        'YOLOv10-seg': {'n': 1.3, 'm': 3.7, 'l': 6.3, 'x': 10.5},
        'YOLOv11-seg': {'n': 1.2, 's': 2.1, 'm': 3.5, 'l': 5.8, 'x': 9.2},
        'YOLOv26-seg': {'n': 1.2, 's': 2.1, 'm': 3.5, 'l': 5.8, 'x': 9.2},
    }
    mult = base_mult.get(family, {}).get(size, 1.2)
    scale = (imgsz / 640) ** 2
    vram_gb = mult * batch * scale * 0.1
    return max(1.2, round(vram_gb, 1))

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

            self.log_signal.emit(f"{tr('Загрузка модели')} {self.model_name}...")
            model = YOLO(self.model_name)
            self.log_signal.emit(tr("Модель загружена. Начинаем обучение..."))

            model.add_callback('on_train_epoch_end', self.on_epoch_end)
            model.add_callback('on_train_batch_end', self.on_batch_end)
            model.add_callback('on_train_end', self.on_train_end)

            if self.task_type == 'classify':
                model.train(data=self.data_yaml, task='classify', **self.params, verbose=True)
            else:
                model.train(data=self.data_yaml, **self.params, verbose=True)
            self.finished_signal.emit(True)
        except Exception as e:
            self.log_signal.emit(f"{tr('Ошибка')}: {str(e)}")
            self.finished_signal.emit(False)
        finally:
            if 'model' in locals():
                del model
            import gc
            gc.collect()
            if TORCH_AVAILABLE and torch.cuda.is_available():
                torch.cuda.empty_cache()
            
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
        metrics = {}
        
        def safe_get_dict(obj):
            try:
                res = obj() if callable(obj) else obj
                if isinstance(res, dict):
                    return res
            except:
                pass
            return {}

        if hasattr(trainer, 'metrics'):
            metrics.update(safe_get_dict(trainer.metrics))
            
        if hasattr(trainer, 'label_loss_items'):
            metrics.update(safe_get_dict(trainer.label_loss_items))
            
        self.epoch_signal.emit(epoch, metrics)

    def on_batch_end(self, trainer):
        if not self._is_running:
            trainer.stop()
            return
        self.pause_mutex.lock()
        if self._paused:
            self.paused_signal.emit()
            self.pause_condition.wait(self.pause_mutex)
        self.pause_mutex.unlock()

    def on_train_end(self, trainer):
        self.log_signal.emit(tr("Обучение завершено."))

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
        self.back_btn = QPushButton(tr("← Вернуться к разметке"))
        self.back_btn.clicked.connect(self.switch_to_annotation)
        top_layout.addWidget(self.back_btn)
        top_layout.addStretch()
        main_layout.addLayout(top_layout)

        tabs = QTabWidget()
        tabs.tabBar().setExpanding(False)
        main_layout.addWidget(tabs)

        # --- Вкладка "Управление" ---
        control_tab = QWidget()
        control_layout = QVBoxLayout(control_tab)
        tabs.addTab(control_tab, tr("Управление"))

        task_group = QGroupBox(tr("Тип задачи"))
        task_layout = QHBoxLayout()
        self.task_detect = QRadioButton(tr("Детекция"))
        self.task_classify = QRadioButton(tr("Классификация"))
        self.task_segment = QRadioButton(tr("Сегментация"))
        self.task_detect.setChecked(True)
        self.task_detect.toggled.connect(self.on_task_changed)
        self.task_detect.toggled.connect(self.update_vram_estimate)
        # Bug #9 fix: task_classify was not connected to on_task_changed
        self.task_classify.toggled.connect(self.on_task_changed)
        self.task_classify.toggled.connect(self.update_vram_estimate)
        self.task_segment.toggled.connect(self.on_task_changed)
        self.task_segment.toggled.connect(self.update_vram_estimate)
        task_layout.addWidget(self.task_detect)
        task_layout.addWidget(self.task_classify)
        task_layout.addWidget(self.task_segment)
        task_layout.addStretch()
        task_group.setLayout(task_layout)
        control_layout.addWidget(task_group)

        model_group = QGroupBox(tr("Выбор модели"))
        model_layout = QFormLayout()

        self.family_combo = QComboBox()
        self.size_combo = QComboBox()
        self.custom_model_edit = QLineEdit()
        self.custom_model_edit.setPlaceholderText(tr("Путь к файлу модели .pt"))
        self.custom_model_edit.setEnabled(False)
        custom_browse = QPushButton(tr("Обзор..."))
        custom_browse.clicked.connect(self.browse_custom_model)
        custom_layout = QHBoxLayout()
        custom_layout.addWidget(self.custom_model_edit)
        custom_layout.addWidget(custom_browse)

        model_layout.addRow(tr("Семейство:"), self.family_combo)
        model_layout.addRow(tr("Размер:"), self.size_combo)
        model_layout.addRow(tr("Custom модель:"), custom_layout)

        model_group.setLayout(model_layout)
        control_layout.addWidget(model_group)

        self.update_family_list('detect')
        self.family_combo.currentTextChanged.connect(self.update_size_list)
        self.family_combo.currentTextChanged.connect(self.update_vram_estimate)
        self.size_combo.currentTextChanged.connect(self.update_vram_estimate)

        form_group = QGroupBox(tr("Параметры обучения"))
        form_layout = QFormLayout()

        self.data_edit = QLineEdit()
        self.data_edit.setPlaceholderText(tr("Путь к data.yaml (или папке для классификации)"))
        data_browse = QPushButton(tr("Обзор..."))
        data_browse.clicked.connect(self.browse_data)
        data_layout = QHBoxLayout()
        data_layout.addWidget(self.data_edit)
        data_layout.addWidget(data_browse)
        form_layout.addRow(tr("Датасет:"), data_layout)

        self.epochs_spin = QSpinBox()
        self.epochs_spin.setRange(1, 1000)
        self.epochs_spin.setValue(100)
        self.epochs_spin.valueChanged.connect(self.update_vram_estimate)
        form_layout.addRow(tr("Эпохи:"), self.epochs_spin)

        self.batch_spin = QSpinBox()
        self.batch_spin.setRange(1, 256)
        self.batch_spin.setValue(16)
        self.batch_spin.valueChanged.connect(self.update_vram_estimate)
        form_layout.addRow(tr("Batch:"), self.batch_spin)

        self.imgsz_spin = QSpinBox()
        self.imgsz_spin.setRange(32, 1280)
        self.imgsz_spin.setValue(640)
        self.imgsz_spin.valueChanged.connect(self.update_vram_estimate)
        form_layout.addRow(tr("Image size:"), self.imgsz_spin)

        self.device_combo = QComboBox()
        self.device_combo.setEditable(True)
        self.device_combo.setInsertPolicy(QComboBox.NoInsert)
        self.populate_device_list()
        self.device_combo.currentTextChanged.connect(self.update_vram_estimate)
        form_layout.addRow(tr("Device:"), self.device_combo)

        self.workers_spin = QSpinBox()
        self.workers_spin.setRange(0, 16)
        if getattr(sys, 'frozen', False):
            self.workers_spin.setValue(0)
            self.workers_spin.setEnabled(False)
            self.workers_spin.setToolTip(tr("В скомпилированной версии workers должен быть 0"))
        else:
            self.workers_spin.setValue(8)
        form_layout.addRow(tr("Workers:"), self.workers_spin)

        self.patience_spin = QSpinBox()
        self.patience_spin.setRange(0, 1000)
        self.patience_spin.setValue(50)
        form_layout.addRow(tr("Patience:"), self.patience_spin)

        # Оптимизации скорости
        self.amp_check = QCheckBox(tr("Смешанная точность (AMP)"))
        self.amp_check.setChecked(True)
        self.amp_check.setToolTip(tr("Ускоряет обучение на GPU и снижает потребление памяти"))
        form_layout.addRow("", self.amp_check)

        self.cache_combo = QComboBox()
        self.cache_combo.addItems([tr("Нет"), "disk", "ram"])
        self.cache_combo.setToolTip(tr("Кэширование изображений для быстрой загрузки"))
        form_layout.addRow(tr("Кэширование:"), self.cache_combo)

        self.rect_check = QCheckBox(tr("Прямоугольное обучение (rect)"))
        self.rect_check.setChecked(False)
        self.rect_check.setToolTip(tr("Оптимизирует обучение для неквадратных изображений"))
        form_layout.addRow("", self.rect_check)

        self.plots_check = QCheckBox(tr("Генерировать графики YOLO"))
        self.plots_check.setChecked(False)
        self.plots_check.setToolTip(tr("Отключите для экономии времени на сохранение визуализаций"))
        form_layout.addRow("", self.plots_check)

        self.project_edit = QLineEdit()
        self.project_edit.setText("runs/train")
        form_layout.addRow(tr("Project:"), self.project_edit)

        self.name_edit = QLineEdit()
        self.name_edit.setText("exp")
        form_layout.addRow(tr("Name:"), self.name_edit)

        self.exist_ok_check = QCheckBox()
        self.exist_ok_check.setChecked(False)
        form_layout.addRow(tr("Exist OK:"), self.exist_ok_check)

        form_group.setLayout(form_layout)
        control_layout.addWidget(form_group)

        self.vram_label = QLabel("")
        self.vram_label.setWordWrap(True)
        control_layout.addWidget(self.vram_label)

        # --- Вкладка "Аугментация" ---
        aug_tab = QWidget()
        aug_layout = QVBoxLayout(aug_tab)

        aug_group = QGroupBox(tr("Параметры аугментации данных"))
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
        reset_btn = QPushButton(tr("Сбросить к значениям по умолчанию"))
        reset_btn.clicked.connect(self.reset_augmentation)
        aug_layout.addWidget(reset_btn)

        aug_layout.addStretch()
        tabs.addTab(aug_tab, tr("Аугментация"))

        # --- Вкладка «Настройки сегментации» ---
        self.seg_tab = QWidget()
        seg_layout = QVBoxLayout(self.seg_tab)
        seg_layout.setContentsMargins(12, 12, 12, 12)
        seg_layout.setSpacing(12)

        # Предупреждение
        warn_group = QGroupBox(tr("Важное предупреждение"))
        warn_group.setStyleSheet(
            "QGroupBox { border: 2px solid #e05555; border-radius: 6px; "
            "margin-top: 6px; padding-top: 4px; color: #e05555; font-weight: bold; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 8px; color: #e05555; }"
        )
        warn_inner = QVBoxLayout()
        warn_label = QLabel(tr(
            "Сегментационные модели YOLO требуют полигональных масок.\n"
            "Аннотации в формате прямоугольных боксов (bbox) НЕ содержат\n"
            "информации о форме объекта — модель, обученная на таких данных,\n"
            "будет возвращать прямоугольные маски вместо точных контуров.\n\n"
            "Рекомендуется разметить объекты полигонами перед запуском обучения."
        ))
        warn_label.setWordWrap(True)
        warn_label.setStyleSheet("color: #f0a0a0; font-size: 10pt; padding: 4px;")
        warn_inner.addWidget(warn_label)
        warn_group.setLayout(warn_inner)
        seg_layout.addWidget(warn_group)

        # Выбор поведения с боксами
        box_mode_group = QGroupBox(tr("Поведение с bbox-аннотациями при экспорте датасета"))
        box_mode_layout = QVBoxLayout()

        self.seg_box_exclude = QRadioButton(tr("Исключить боксы из датасета (безопасно, рекомендуется)"))
        self.seg_box_exclude.setChecked(True)
        self.seg_box_exclude.setToolTip(tr(
            "Аннотации без полигона будут пропущены при подготовке датасета. "
            "Гарантирует корректные маски, но уменьшает объём данных."
        ))

        self.seg_box_convert = QRadioButton(tr("Конвертировать bbox в прямоугольный полигон"))
        self.seg_box_convert.setToolTip(tr(
            "Бокс будет преобразован в полигон из 4 вершин. "
            "Маска будет прямоугольной — точность ниже, чем при ручной разметке."
        ))

        self.seg_box_keep = QRadioButton(tr("Использовать боксы как есть (только для опытных)"))
        self.seg_box_keep.setToolTip(tr(
            "Оставить аннотации без изменений. Результат непредсказуем."
        ))

        box_mode_layout.addWidget(self.seg_box_exclude)
        box_mode_layout.addWidget(self.seg_box_convert)
        box_mode_layout.addWidget(self.seg_box_keep)

        self.seg_keep_warn = QLabel(
            "⚠️ " + tr("Внимание: боксы без масок дадут прямоугольные сегменты. "
                        "Качество сегментации будет очень низким.")
        )
        self.seg_keep_warn.setWordWrap(True)
        self.seg_keep_warn.setStyleSheet("color: #e09020; font-style: italic; padding-left: 20px;")
        self.seg_keep_warn.setVisible(False)
        box_mode_layout.addWidget(self.seg_keep_warn)

        self.seg_box_keep.toggled.connect(self.seg_keep_warn.setVisible)

        box_mode_group.setLayout(box_mode_layout)
        seg_layout.addWidget(box_mode_group)

        hint_label = QLabel(
            "💡 " + tr("Эти настройки применяются при подготовке датасета. "
                       "Во время обучения VisionForge использует готовый data.yaml.")
        )
        hint_label.setWordWrap(True)
        hint_label.setStyleSheet("color: #80a0c0; font-size: 9pt; padding: 4px;")
        seg_layout.addWidget(hint_label)
        seg_layout.addStretch()

        self.seg_tab_index = tabs.addTab(self.seg_tab, tr("Сегментация ▶"))
        self.tabs_widget = tabs

        # Скрываем вкладку — активна только при выборе «Сегментация»
        tabs.setTabVisible(self.seg_tab_index, False)
        self.task_segment.toggled.connect(self._on_segment_tab_visibility)

        # --- Кнопки управления обучением ---
        btn_layout = QHBoxLayout()
        self.start_btn = QPushButton(tr("Старт"))
        self.start_btn.clicked.connect(self.start_training)
        self.pause_btn = QPushButton(tr("Пауза"))
        self.pause_btn.setEnabled(False)
        self.pause_btn.clicked.connect(self.toggle_pause)
        self.stop_btn = QPushButton(tr("Стоп"))
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

        self.time_label = QLabel(tr("Осталось: --:--:--"))
        self.time_label.setAlignment(Qt.AlignCenter)
        control_layout.addWidget(self.time_label)

        # --- Вкладка графиков ---
        plot_tab = QWidget()
        plot_layout = QVBoxLayout(plot_tab)
        tabs.addTab(plot_tab, tr("Графики"))

        self.figure = Figure(figsize=(8, 6))
        self.canvas = FigureCanvas(self.figure)
        plot_layout.addWidget(self.canvas)

        self.ax1 = self.figure.add_subplot(211)
        self.ax2 = self.figure.add_subplot(212)
        self.ax1.set_xlabel(tr('Epoch'))
        self.ax2.set_xlabel(tr('Epoch'))
        self.figure.tight_layout()

        # --- Вкладка логов ---
        log_tab = QWidget()
        log_layout = QVBoxLayout(log_tab)
        tabs.addTab(log_tab, tr("Логи"))

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
            task = self._current_task()
            device = self.get_device_string()

            if family == 'Custom' or not size:
                self.vram_label.setText("")
                return

            if task == 'detect':
                vram_needed = estimate_vram_detection(family, size, imgsz, batch)
            elif task == 'segment':
                vram_needed = estimate_vram_segmentation(family, size, imgsz, batch)
            else:
                vram_needed = estimate_vram_classification(family, size, imgsz, batch)

            available = self.get_available_memory()
            if available is not None:
                if vram_needed > available * 0.9:
                    color = "red"
                    msg = (f"⚠️ {tr('Оценочное потребление')} {vram_needed:.1f} GB {tr('превышает 90% доступной памяти')} "
                           f"({available:.1f} GB). {tr('Возможен Out of Memory!')}")
                elif vram_needed > available * 0.7:
                    color = "orange"
                    msg = (f"⚠️ {tr('Оценочное потребление')} {vram_needed:.1f} GB {tr('близко к доступной памяти')} "
                           f"({available:.1f} GB). {tr('Риск нехватки.')}")
                else:
                    color = "green"
                    msg = (f"✅ {tr('Оценочное потребление')} {vram_needed:.1f} GB. {tr('Доступно')} "
                           f"{available:.1f} GB. {tr('Должно хватить.')}")
            else:
                msg = (f"⚠️ {tr('Приблизительное потребление памяти')}: ~{vram_needed} GB. "
                       f"{tr('Не удалось определить доступную память.')}")
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
        task = self._current_task()
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
        task = self._current_task()
        self.update_family_list(task)
        self.update_size_list()
        self.update_vram_estimate()

    def _on_segment_tab_visibility(self, checked):
        """Показывает/скрывает вкладку настроек сегментации."""
        self.tabs_widget.setTabVisible(self.seg_tab_index, checked)

    def _current_task(self):
        if self.task_detect.isChecked():
            return 'detect'
        elif self.task_segment.isChecked():
            return 'segment'
        else:
            return 'classify'

    def browse_custom_model(self):
        path, _ = QFileDialog.getOpenFileName(self, tr("Выберите файл модели"), "", "Model files (*.pt)")
        if path:
            self.custom_model_edit.setText(path)

    def browse_data(self):
        if self.task_detect.isChecked() or self.task_segment.isChecked():
            path, _ = QFileDialog.getOpenFileName(self, "data.yaml", "", "YAML files (*.yaml)")
        else:
            path = QFileDialog.getExistingDirectory(self, tr("Dataset folder"))
        if path:
            self.data_edit.setText(path)

    def get_model_path(self):
        family = self.family_combo.currentText()
        if family == 'Custom':
            return self.custom_model_edit.text()
        size = self.size_combo.currentText()
        task = self._current_task()
        if task == 'detect':
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
        elif task == 'segment':
            if family.startswith('YOLOv8'):
                return f"yolov8{size}-seg.pt"
            elif family.startswith('YOLOv9'):
                return f"yolov9{size}-seg.pt"
            elif family.startswith('YOLOv10'):
                return f"yolov10{size}-seg.pt"
            elif family.startswith('YOLOv11'):
                return f"yolo11{size}-seg.pt"
            elif family.startswith('YOLOv26'):
                return f"yolo26{size}-seg.pt"
            else:
                return f"yolov8{size}-seg.pt"
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
            'device': self.get_device_string(),
            'amp': self.amp_check.isChecked(),
            'rect': self.rect_check.isChecked(),
            'plots': self.plots_check.isChecked()
        }

        cache_val = self.cache_combo.currentText()
        if cache_val == tr("Нет"):
            params['cache'] = False
        else:
            params['cache'] = cache_val

        # Параметры аугментации
        for name, widget in self.aug_widgets.items():
            params[name] = widget.value()

        # Режим обработки боксов для сегментации
        if self.task_segment.isChecked():
            if self.seg_box_convert.isChecked():
                params['seg_box_mode'] = 'convert'
            elif self.seg_box_keep.isChecked():
                params['seg_box_mode'] = 'keep'
            else:
                params['seg_box_mode'] = 'exclude'

        return params

    def start_training(self):
        task = self._current_task()
        model_path = self.get_model_path()
        data_path = self.data_edit.text()
        if self.family_combo.currentText() == 'Custom':
            if not os.path.exists(model_path):
                QMessageBox.warning(self, tr("Ошибка"), f"{tr('Файл модели не найден')}: {model_path}")
                return
        if not os.path.exists(data_path):
            QMessageBox.warning(self, tr("Ошибка"), f"{tr('Датасет не найден')}: {data_path}")
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
        self.time_label.setText(tr("Осталось: --:--:--"))
        self.start_time = time.time()
        self.last_epoch_time = 0
        self.avg_epoch_time = 0

        self.worker = TrainWorker(task, model_path, data_path, params)
        self.worker.log_signal.connect(self.add_log)
        self.worker.epoch_signal.connect(self.on_epoch_update)
        self.worker.finished_signal.connect(self.on_training_finished)
        self.worker.paused_signal.connect(self.on_paused)
        self.worker.start()

        self.stop_btn.setEnabled(True)
        self.pause_btn.setEnabled(True)
        self.start_btn.setEnabled(False)
        self.add_log(tr("Обучение запущено..."))

    def toggle_pause(self):
        if self.worker is None:
            return
        if self.pause_btn.text() == tr("Пауза"):
            self.worker.pause()
            self.pause_btn.setText(tr("Продолжить"))
            self.add_log(tr("Обучение приостановлено."))
        else:
            self.worker.resume()
            self.pause_btn.setText(tr("Пауза"))
            self.add_log(tr("Обучение возобновлено."))

    def stop_training(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.add_log(tr("Остановка обучения..."))
            if not self.worker.wait(2000):
                self.worker.terminate()
                self.worker.wait()
            self.stop_btn.setEnabled(False)
            self.pause_btn.setEnabled(False)
            self.start_btn.setEnabled(True)
            self.add_log(tr("Обучение остановлено."))
            self.time_label.setText(tr("Осталось: --:--:--"))

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
            self.time_label.setText(f"{tr('Осталось')}: {hours:02d}:{minutes:02d}:{seconds:02d}")
        else:
            self.time_label.setText(tr("Осталось: --:--:--"))

        self.epochs_data.append(epoch)

        if self.task_detect.isChecked() or self.task_segment.isChecked():
            # Потери
            # Пытаемся найти ключи в разных форматах (train/ или без префикса)
            box_loss = metrics.get('train/box_loss', metrics.get('box_loss', 0))
            cls_loss = metrics.get('train/cls_loss', metrics.get('cls_loss', 0))
            dfl_loss = metrics.get('train/dfl_loss', metrics.get('dfl_loss', 0))
            seg_loss = metrics.get('train/seg_loss', metrics.get('seg_loss', 0)) # для сегментации
            
            self.loss_data.setdefault('box_loss', []).append(box_loss)
            self.loss_data.setdefault('cls_loss', []).append(cls_loss)
            self.loss_data.setdefault('dfl_loss', []).append(dfl_loss)
            if self.task_segment.isChecked():
                self.loss_data.setdefault('seg_loss', []).append(seg_loss)

            # mAP
            map50 = metrics.get('metrics/mAP50(B)', metrics.get('mAP50', metrics.get('map50', 0)))
            map95 = metrics.get('metrics/mAP50-95(B)', metrics.get('mAP50-95', metrics.get('map50-95', 0)))
            # Если сегментация, mAP может называться по-другому в metrics/mAP50(M)
            if self.task_segment.isChecked():
                map50_m = metrics.get('metrics/mAP50(M)', 0)
                if map50_m > 0: map50 = map50_m
                map95_m = metrics.get('metrics/mAP50-95(M)', 0)
                if map95_m > 0: map95 = map95_m

            self.map_data.append(map50)
            self.map95_data.append(map95)

            # Precision, Recall
            prec = metrics.get('metrics/precision(B)', metrics.get('precision', metrics.get('precision(B)', 0)))
            rec = metrics.get('metrics/recall(B)', metrics.get('recall', metrics.get('recall(B)', 0)))
            self.precision_data.append(prec)
            self.recall_data.append(rec)

            loss_msg = (f"{tr('Эпоха')} {epoch}: box={box_loss:.4f}, cls={cls_loss:.4f}, dfl={dfl_loss:.4f}")
            if self.task_segment.isChecked():
                loss_msg += f", seg={seg_loss:.4f}"
            loss_msg += f", mAP50={map50:.4f}, mAP95={map95:.4f}, P={prec:.4f}, R={rec:.4f}"
        else:
            # Классификация
            loss = metrics.get('train/loss', metrics.get('loss', 0))
            acc = metrics.get('metrics/accuracy_top1', metrics.get('accuracy', metrics.get('accuracy_top1', 0)))
            self.loss_data.setdefault('loss', []).append(loss)
            self.acc_data.append(acc)
            loss_msg = f"{tr('Эпоха')} {epoch}: loss={loss:.4f}, acc={acc:.4f}"

        self.add_log(loss_msg)
        self.update_plot()

    def update_plot(self):
        self.ax1.clear()
        self.ax2.clear()
        if self.epochs_data:
            if self.task_detect.isChecked() or self.task_segment.isChecked():
                # Потери
                if 'box_loss' in self.loss_data:
                    self.ax1.plot(self.epochs_data, self.loss_data['box_loss'], label='box_loss')
                if 'cls_loss' in self.loss_data:
                    self.ax1.plot(self.epochs_data, self.loss_data['cls_loss'], label='cls_loss')
                if 'dfl_loss' in self.loss_data:
                    self.ax1.plot(self.epochs_data, self.loss_data['dfl_loss'], label='dfl_loss')
                if 'seg_loss' in self.loss_data:
                    self.ax1.plot(self.epochs_data, self.loss_data['seg_loss'], label='seg_loss')
                
                self.ax1.legend()
                self.ax1.set_ylabel(tr('Loss'))
                self.ax1.set_title(tr('Loss'))
                self.ax1.set_xlabel(tr('Epoch'))

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
                self.ax2.set_ylabel(tr('Metrics'))
                self.ax2.set_title(tr('Metrics'))
                self.ax2.set_xlabel(tr('Epoch'))
            else:
                # Классификация
                if self.loss_data.get('loss'):
                    self.ax1.plot(self.epochs_data, self.loss_data['loss'], label='loss', color='red')
                    self.ax1.legend()
                    self.ax1.set_ylabel(tr('Loss'))
                    self.ax1.set_title(tr('Loss'))
                    self.ax1.set_xlabel(tr('Epoch'))
                if self.acc_data:
                    self.ax2.plot(self.epochs_data, self.acc_data, label='accuracy', color='blue')
                    self.ax2.legend()
                    self.ax2.set_ylabel(tr('Accuracy'))
                    self.ax2.set_title(tr('Accuracy'))
                    self.ax2.set_xlabel(tr('Epoch'))
        
        self.figure.tight_layout()
        self.canvas.draw()

    def on_training_finished(self, success):
        self.start_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        self.pause_btn.setText(tr("Пауза"))
        if success:
            self.add_log(tr("Обучение успешно завершено."))
        else:
            self.add_log(tr("Обучение завершено с ошибкой."))
        self.time_label.setText(tr("Осталось: --:--:--"))

    def add_log(self, msg):
        self.log_text.append(msg)
        self.log_text.moveCursor(self.log_text.textCursor().End)