# ui/main_window.py
import os
import sys
import cv2
import hashlib
import json
import shutil

from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QListWidget, QListWidgetItem,
                             QGroupBox, QFileDialog, QMessageBox, QInputDialog,
                             QDialog, QComboBox, QStackedWidget, QAction,
                             QSplitter, QRadioButton, QColorDialog, QMenu, QProgressBar)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QSize, QThread
from PyQt5.QtGui import QPixmap, QPainter, QColor, QPen, QCursor
from ui.theme import get_current_theme_style
from ui.statistics_dialog import StatisticsDialog
project_root = os.path.dirname(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core.annotation_widget import AnnotationWidget
from core.thumbnail_bar import ThumbnailBar
from core.type_dialog import TypeDialog
from project.project_manager import Project
from ui.settings_dialog import SettingsDialog
from ui.training_widget import TrainingWidget
from ui.batch_dialog import BatchDialog, ProgressDialog
from ui.prepare_dataset_dialog import PrepareDatasetDialog
from ui.class_hierarchy_widget import ClassHierarchyWidget
import config
from ultralytics import YOLO
from core.utils import LimitedSizeDict
from config import VERSION
from core.i18n import tr
class BatchWorker(QThread):
    progress = pyqtSignal(int, str)  # текущий индекс, имя файла
    finished = pyqtSignal(bool, str)  # успех, сообщение
    # NOTE: instance attribute — do NOT make this a class attribute (shared across instances)

    def __init__(self, images, project, detector, classifier, params, source_dir=None):
        super().__init__()
        self.cancelled = False        # instance attribute — must NOT be class-level
        self.images = images          # список имён файлов (только имена, без пути)
        self.project = project        # текущий проект (для сохранения результатов)
        self.detector = detector
        self.classifier = classifier
        self.params = params
        self.source_dir = source_dir if source_dir is not None else project.images_dir
        self.auto_project = None      # будет установлен из main_window

    def run(self):
        try:
            total = len(self.images)
            for i, filename in enumerate(self.images):
                if self.cancelled:
                    self.finished.emit(False, tr("Отменено пользователем"))
                    return
                self.progress.emit(i, filename)
                self.process_one(filename)
            self.finished.emit(True, f"{tr('Обработано')} {total} {tr('изображений')}")
        except Exception as e:
            self.finished.emit(False, f"{tr('Ошибка')}: {str(e)}")

    def process_one(self, filename):
        src_path = os.path.join(self.source_dir, filename)
        dst_path = os.path.join(self.auto_project.images_dir, filename)
        os.makedirs(os.path.dirname(dst_path), exist_ok=True)
        shutil.copy2(src_path, dst_path)

        img = cv2.imread(src_path)
        if img is None:
            return
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        results = self.detector(img_rgb, conf=self.params["conf"], iou=self.params["iou"], verbose=False)[0]
        boxes = results.boxes
        if boxes is None or len(boxes) == 0:
            return

        new_boxes = []
        for box in boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            class_name = "unknown"
            if self.params["use_classifier"] and self.classifier is not None:
                crop = img_rgb[y1:y2, x1:x2]
                if crop.size > 0 and crop.shape[0] >= 10 and crop.shape[1] >= 10:
                    cls_results = self.classifier(crop, verbose=False)
                    probs = cls_results[0].probs
                    if probs is not None:
                        top_conf = probs.top1conf.item()
                        top_class_id = probs.top1
                        if top_conf >= self.params["cls_conf"]:
                            class_name = self.classifier.names[top_class_id]
            new_boxes.append({"bbox": [x1, y1, x2, y2], "class": class_name})

        if new_boxes:
            self.auto_project.annotations[filename] = new_boxes
            self.auto_project.image_types[filename] = set(b["class"] for b in new_boxes)
            for b in new_boxes:
                if b["class"] not in self.auto_project.classes:
                    self.auto_project.classes.append(b["class"])
            self.auto_project.classes.sort()
            self.auto_project.generate_class_colors()

    def cancel(self):
        self.cancelled = True


class BoxItemWidget(QWidget):
    """Виджет для элемента списка боксов с кнопкой удаления (крестик)."""
    delete_clicked = pyqtSignal(int)

    def __init__(self, text, index, parent=None):
        super().__init__(parent)
        self.index = index
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(8)

        self.label = QLabel(text)
        self.label.setStyleSheet("color: #f4f4f5; font-size: 12px;")
        layout.addWidget(self.label)

        layout.addStretch()

        self.delete_btn = QPushButton("✕")
        self.delete_btn.setFixedSize(18, 18)
        self.delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #ef4444;
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 12px;
                font-weight: bold;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: #f87171;
            }
        """)
        self.delete_btn.clicked.connect(self.on_delete)
        layout.addWidget(self.delete_btn)

    def on_delete(self):
        self.delete_clicked.emit(self.index)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(tr("VisionForge - Инструмент разметки"))
        self.setGeometry(100, 100, 1300, 800)
        self.setStyleSheet(get_current_theme_style())  # тема из ui.theme

        # Данные проекта
        self.main_project = Project(config.SCREENSHOTS_DIR, config.MAIN_JSON)
        self.auto_project = Project(config.AUTO_IMAGES_DIR, config.AUTO_JSON)
        self.current_project = self.main_project
        self.current_mode = 'main'
        self.current_index = 0
        self.filtered_images = []
        self.filter_type = tr("Все")

        # Модели
        self.detector = None
        self.classifier = None

        # Кэш миниатюр (in‑memory)
        self.thumb_memory_cache = LimitedSizeDict(maxsize=200)

        # Настройка автоскрытия панели
        self.auto_hide_panel = config.AUTO_HIDE_PANEL

        # Центральный стек
        self.central_stack = QStackedWidget()
        self.setCentralWidget(self.central_stack)

        # Виджет разметки
        self.annotation_container = QWidget()
        self.setup_annotation_ui()
        self.central_stack.addWidget(self.annotation_container)

        # Виджет обучения
        self.training_widget = TrainingWidget(detector=self.detector, classifier=self.classifier)
        self.training_widget.switch_to_annotation.connect(self.switch_to_annotation_mode)
        self.central_stack.addWidget(self.training_widget)

        # Статус бар
        self.status_label = QLabel(tr("Готов к работе"))
        self.status_label.setStyleSheet("color: #0d7377; font-weight: bold;")
        self.statusBar().addWidget(self.status_label, 1)

        # Меню
        self.create_menus()

        # Загружаем модели
        self.load_models_from_config()

        # Безопасная загрузка проектов
        ok_main, msg_main = self.safe_load_project(self.main_project)
        if not ok_main:
            print(f"{tr('Предупреждение')}: {tr('основной проект повреждён')} ({msg_main}). {tr('Создаётся новый.')}")
            self._reset_project(self.main_project)

        ok_auto, msg_auto = self.safe_load_project(self.auto_project)
        if not ok_auto:
            print(f"{tr('Предупреждение')}: {tr('авто-проект повреждён')} ({msg_auto}). {tr('Создаётся новый.')}")
            self._reset_project(self.auto_project)

        self.current_project = self.main_project

        # Обновляем интерфейс после загрузки
        self.update_filter_combo()
        self.update_filtered_images()

        # Заполняем панель миниатюр
        self.thumb_bar.clear()
        for f in self.filtered_images:
            self.thumb_bar.add_item(f)
        self.thumb_bar.load_visible_thumbnails()

        self.load_current_image()

        from core.i18n import get_translator
        get_translator().languageChanged.connect(self.retranslate_ui)

        # Показать хаб проектов при запуске (отложенно, чтобы окно успело появиться)
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(0, self.show_project_hub)

    # ---------- Вспомогательные методы для безопасной загрузки ----------
    def safe_load_project(self, project):
        try:
            project.load()
            return True, ""
        except Exception as e:
            return False, str(e)

    def _reset_project(self, project):
        project.images_list = [f for f in os.listdir(project.images_dir)
                               if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        project.annotations = {}
        project.image_types = {img: set() for img in project.images_list}
        project.classes = ["unknown"]
        project.class_hierarchy = ["unknown"]
        project.generate_class_colors()
        project.save()

    def after_project_load(self):
        """Обновляет интерфейс после загрузки нового проекта."""
        self.update_filter_combo()
        self.update_filtered_images()
        
        self.current_index = 0
        if getattr(self.current_project, 'last_image', None) and self.current_project.last_image in self.filtered_images:
            self.current_index = self.filtered_images.index(self.current_project.last_image)
            
        self.load_current_image()
        self.thumb_bar.clear()
        for f in self.filtered_images:
            self.thumb_bar.add_item(f)
        self.thumb_bar.load_visible_thumbnails()
        if self.current_project.classes:
            self.widget.current_class = self.current_project.classes[0]
            self.widget.set_classes(self.current_project.classes, self.widget.current_class)
            self.class_label.setText(f"{tr('Класс')}: {self.widget.current_class}")
        self.update_class_tree()
        self.current_project.save()  # необязательно, но для синхронизации
        
        # Добавляем в недавние проекты
        import config
        folder = self.current_project.images_dir
        json_path = self.current_project.annotations_file
        name = os.path.basename(folder)
        thumb = ""
        if getattr(self.current_project, 'last_image', None) and self.current_project.last_image in self.filtered_images:
            thumb = os.path.join(folder, self.current_project.last_image)
        elif self.filtered_images:
            thumb = os.path.join(folder, self.filtered_images[0])
            
        config.add_recent_project({
            "path": folder,
            "json_path": json_path,
            "name": name,
            "thumbnail": thumb,
            "description": ""
        })
        
        # Обновляем глобальные пути
        cfg = config.load_config()
        cfg["main_images_dir"] = folder
        cfg["main_json"] = json_path
        config.save_config(cfg)

    # ---------- Меню ----------
    def create_menus(self):
        menubar = self.menuBar()
        menubar.clear()

        # Файл
        self.file_menu = menubar.addMenu(tr('Файл'))

        new_project_action = QAction(tr('Новый проект'), self)
        new_project_action.triggered.connect(self.new_project)
        self.file_menu.addAction(new_project_action)

        open_project_action = QAction(tr('Открыть проект'), self)
        open_project_action.triggered.connect(self.open_project)
        self.file_menu.addAction(open_project_action)

        save_project_action = QAction(tr('Сохранить проект'), self)
        save_project_action.triggered.connect(self.save_project)
        self.file_menu.addAction(save_project_action)

        save_project_as_action = QAction(tr('Сохранить проект как...'), self)
        save_project_as_action.triggered.connect(self.save_project_as)
        self.file_menu.addAction(save_project_as_action)

        self.file_menu.addSeparator()

        import_action = QAction(tr('Импорт аннотаций...'), self)
        import_action.triggered.connect(self.import_annotations)
        self.file_menu.addAction(import_action)

        self.file_menu.addSeparator()

        self.export_menu = self.file_menu.addMenu(tr('Экспорт'))
        export_yolo_action = QAction(tr('YOLO'), self)
        export_yolo_action.triggered.connect(self.export_yolo)
        self.export_menu.addAction(export_yolo_action)
        export_coco_action = QAction(tr('COCO'), self)
        export_coco_action.triggered.connect(self.export_coco)
        self.export_menu.addAction(export_coco_action)
        export_voc_action = QAction(tr('Pascal VOC'), self)
        export_voc_action.triggered.connect(self.export_voc)
        self.export_menu.addAction(export_voc_action)

        self.file_menu.addSeparator()
        exit_action = QAction(tr('Выход'), self)
        exit_action.triggered.connect(self.close)
        self.file_menu.addAction(exit_action)

        # Инструменты
        self.tools_menu = menubar.addMenu(tr('Инструменты'))

        detection_action = QAction(tr('Детекция в реальном времени'), self)
        detection_action.triggered.connect(self.start_overlay)
        self.tools_menu.addAction(detection_action)

        batch_action = QAction(tr('Пакетная разметка'), self)
        batch_action.triggered.connect(self.batch_process)
        self.tools_menu.addAction(batch_action)

        prepare_dataset_action = QAction(tr('Подготовить датасет'), self)
        prepare_dataset_action.triggered.connect(self.prepare_dataset)
        self.tools_menu.addAction(prepare_dataset_action)

        stats_action = QAction(tr('Статистика проекта'), self)
        stats_action.triggered.connect(self.show_statistics)
        self.tools_menu.addAction(stats_action)

        # Обучение
        self.train_menu = menubar.addMenu(tr('Обучение'))
        train_action = QAction(tr('Открыть обучение'), self)
        train_action.triggered.connect(self.switch_to_training_mode)
        self.train_menu.addAction(train_action)

        # Настройки
        self.settings_menu = menubar.addMenu(tr('Настройки'))
        settings_action = QAction(tr('Параметры'), self)
        settings_action.triggered.connect(self.open_settings)
        self.settings_menu.addAction(settings_action)

        # Справка
        self.help_menu = menubar.addMenu(tr('Справка'))
        help_action = QAction(tr('Горячие клавиши'), self)
        help_action.triggered.connect(self.show_help)
        self.help_menu.addAction(help_action)
        about_action = QAction(tr('О программе'), self)
        about_action.triggered.connect(self.show_about)
        self.help_menu.addAction(about_action)

    # ---------- Интерфейс разметки ----------
    def setup_annotation_ui(self):
        """Создаёт интерфейс разметки с компактной правой панелью и деревом классов."""
        main_widget = self.annotation_container
        layout = QVBoxLayout(main_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ====== ВИДЖЕТ АННОТАЦИИ (Инициализируем заранее, т.к. к нему привязаны кнопки) ======
        self.widget = AnnotationWidget()
        self.widget.selection_changed.connect(self.on_selection_changed)
        self.widget.status_message.connect(self.update_status)
        self.widget.boxes_changed.connect(self.on_boxes_changed)
        self.widget.show_type_dialog_requested.connect(self.open_type_dialog)

        # ====== HUD OVERLAY ======
        hud_layout = QVBoxLayout(self.widget)
        hud_layout.setContentsMargins(0, 15, 0, 0)
        hud_layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        
        hud_container = QWidget()
        hud_container.setStyleSheet("background: transparent;")
        
        top_bar = QHBoxLayout(hud_container)
        top_bar.setContentsMargins(0, 0, 0, 0)
        top_bar.setSpacing(4)
        
        btn_style = "QPushButton { padding: 0px; background-color: rgba(60,60,60,180); color: white; border: 1px solid #555; border-radius: 12px; font-weight: bold; } QPushButton:hover { background-color: rgba(80,80,80,200); }"
        
        self.btn_prev = QPushButton(tr("◀"))
        self.btn_prev.setFixedSize(28, 28)
        self.btn_prev.setStyleSheet(btn_style)
        self.btn_prev.setToolTip(tr("Предыдущее изображение"))
        self.btn_prev.clicked.connect(self.prev_image)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedSize(250, 24)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setAlignment(Qt.AlignCenter)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 12px;
                background-color: rgba(24, 24, 27, 180);
                color: white;
                font-family: 'Segoe UI', 'Inter', 'Roboto', sans-serif;
                font-weight: bold;
                font-size: 13px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: rgba(99, 102, 241, 180); /* Indigo */
                border-radius: 10px;
                margin: 2px;
            }
        """)
        
        self.btn_next = QPushButton(tr("▶"))
        self.btn_next.setFixedSize(28, 28)
        self.btn_next.setStyleSheet(btn_style)
        self.btn_next.setToolTip(tr("Следующее изображение"))
        self.btn_next.clicked.connect(self.next_image)
        
        top_bar.addWidget(self.btn_prev)
        top_bar.addWidget(self.progress_bar)
        top_bar.addWidget(self.btn_next)
        
        hud_layout.addWidget(hud_container)
        
        # ====== MIDDLE SECTION ======
        middle_layout = QHBoxLayout()
        middle_layout.setContentsMargins(0, 0, 0, 0)
        middle_layout.setSpacing(0)
        
        # --- LEFT TOOLBAR ---
        left_toolbar = QVBoxLayout()
        left_toolbar.setContentsMargins(5, 10, 5, 10)
        left_toolbar.setSpacing(8)
        left_toolbar.setAlignment(Qt.AlignTop)
        
        btn_style = """
            QPushButton {
                font-size: 16px;
                padding: 0px;
                background-color: #27272a;
                border: 1px solid #3f3f46;
                border-radius: 6px;
            }
            QPushButton:hover { background-color: #3f3f46; }
            QPushButton:checked { background-color: #4f46e5; border: 1px solid #818cf8; }
        """
        
        self.btn_box_mode = QPushButton("⬜")
        self.btn_box_mode.setFixedSize(36, 36)
        self.btn_box_mode.setCheckable(True)
        self.btn_box_mode.setChecked(True)
        self.btn_box_mode.setToolTip(tr("Бокс (B)"))
        self.btn_box_mode.setStyleSheet(btn_style)
        self.btn_box_mode.clicked.connect(self.set_box_mode)
        
        self.btn_poly_mode = QPushButton("⬡")
        self.btn_poly_mode.setFixedSize(36, 36)
        self.btn_poly_mode.setCheckable(True)
        self.btn_poly_mode.setToolTip(tr("Полигон (P)"))
        self.btn_poly_mode.setStyleSheet(btn_style)
        self.btn_poly_mode.clicked.connect(self.set_poly_mode)
        
        self.btn_auto = QPushButton("🤖")
        self.btn_auto.setFixedSize(36, 36)
        self.btn_auto.setToolTip(tr("Авторазметка (A)"))
        self.btn_auto.setStyleSheet(btn_style)
        self.btn_auto.clicked.connect(self.auto_annotate)
        
        self.btn_next_class = QPushButton("⏩")
        self.btn_next_class.setFixedSize(36, 36)
        self.btn_next_class.setToolTip(tr("След. класс (T)"))
        self.btn_next_class.setStyleSheet(btn_style)
        self.btn_next_class.clicked.connect(self.next_class)
        
        self.btn_delete_image = QPushButton("🗑️")
        self.btn_delete_image.setFixedSize(36, 36)
        self.btn_delete_image.setToolTip(tr("Удалить изобр. (Ctrl+D)"))
        del_style = btn_style + "QPushButton { color: #ff4c4c; }"
        self.btn_delete_image.setStyleSheet(del_style)
        self.btn_delete_image.clicked.connect(self.delete_current_image)
        
        left_toolbar.addWidget(self.btn_box_mode)
        left_toolbar.addWidget(self.btn_poly_mode)
        left_toolbar.addWidget(self.btn_auto)
        left_toolbar.addWidget(self.btn_next_class)
        left_toolbar.addWidget(self.btn_delete_image)
        left_toolbar.addStretch()
        
        left_panel = QWidget()
        left_panel.setFixedWidth(56) # Увеличена ширина панели
        left_panel.setStyleSheet("background-color: #18181b;")
        left_panel.setLayout(left_toolbar)
        
        middle_layout.addWidget(left_panel)
        
        # --- SPLITTER ---
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(2)
        splitter.setStyleSheet("QSplitter::handle { background-color: #3c3c3c; }")

        splitter.addWidget(self.widget)

        # Правая панель
        right_panel = QWidget()
        right_panel.setObjectName("right_panel")
        right_panel.setMinimumWidth(200)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(4, 8, 4, 8)
        right_layout.setSpacing(2)

        # Группа переключения режимов
        self.mode_group = QGroupBox(tr("Режим"))
        mode_layout = QHBoxLayout()
        mode_layout.setContentsMargins(4, 8, 4, 8)
        mode_layout.setSpacing(2)
        self.main_radio = QRadioButton(tr("Основной"))
        self.auto_radio = QRadioButton(tr("Авто"))
        self.main_radio.setChecked(self.current_mode == 'main')
        self.auto_radio.setChecked(self.current_mode == 'auto')
        self.main_radio.toggled.connect(self.on_mode_changed)
        mode_layout.addWidget(self.main_radio)
        mode_layout.addWidget(self.auto_radio)

        self.transfer_btn = QPushButton(tr("→ В основной"))
        self.transfer_btn.setEnabled(False)
        self.transfer_btn.clicked.connect(self.transfer_to_main)
        self.transfer_btn.setFixedWidth(80)
        mode_layout.addWidget(self.transfer_btn)

        self.mode_group.setLayout(mode_layout)
        right_layout.addWidget(self.mode_group)

        # Группа фильтрации по классу
        self.filter_group = QGroupBox(tr("Фильтр"))
        filter_layout = QVBoxLayout()
        filter_layout.setContentsMargins(4, 8, 4, 8)
        filter_layout.setSpacing(6)
        self.filter_combo = QComboBox()
        self.filter_combo.addItem(tr("Все"))
        self.filter_combo.currentTextChanged.connect(self.on_filter_changed)
        filter_layout.addWidget(self.filter_combo)
        self.filter_group.setLayout(filter_layout)
        right_layout.addWidget(self.filter_group)

        # Группа классов с деревом иерархии
        self.classes_group = QGroupBox(tr("Классы"))
        classes_layout = QVBoxLayout()
        classes_layout.setContentsMargins(4, 8, 4, 8)
        classes_layout.setSpacing(2)

        self.class_tree = ClassHierarchyWidget()
        self.class_tree.class_selected.connect(self.on_class_selected_from_list)
        self.class_tree.color_change_requested.connect(self.on_class_color_changed)
        self.class_tree.hierarchy_changed.connect(self.on_hierarchy_changed)
        self.class_tree.delete_class_requested.connect(self.on_class_deleted_from_tree)
        hierarchy_btn_layout = QHBoxLayout()
        self.add_group_btn = QPushButton(tr("+ Группа"))
        self.add_group_btn.clicked.connect(self.add_class_group)
        self.expand_all_btn = QPushButton(tr("Развернуть всё"))
        self.expand_all_btn.clicked.connect(self.class_tree.expandAll)
        self.collapse_all_btn = QPushButton(tr("Свернуть всё"))
        self.collapse_all_btn.clicked.connect(self.class_tree.collapseAll)
        hierarchy_btn_layout.addWidget(self.add_group_btn)
        hierarchy_btn_layout.addWidget(self.expand_all_btn)
        hierarchy_btn_layout.addWidget(self.collapse_all_btn)
        classes_layout.addLayout(hierarchy_btn_layout)

        classes_layout.addWidget(self.class_tree)
        
        self.btn_classes = QPushButton(tr("Редактировать список классов..."))
        self.btn_classes.clicked.connect(self.open_type_dialog)
        classes_layout.addWidget(self.btn_classes)

        self.classes_group.setLayout(classes_layout)
        right_layout.addWidget(self.classes_group)

        # Группа информации
        self.info_group = QGroupBox(tr("Информация"))
        info_layout = QVBoxLayout()
        info_layout.setContentsMargins(4, 8, 4, 8)
        info_layout.setSpacing(2)
        self.total_label = QLabel(f"{tr('Всего')}: 0")
        self.total_label.setStyleSheet("font-size: 12px; font-weight: bold;")
        self.unannotated_label = QLabel(f"{tr('Неразмечено')}: 0")
        self.unannotated_label.setStyleSheet("font-size: 12px;")
        self.class_label = QLabel(f"{tr('Класс')}: {tr('unknown')}")
        self.class_label.setStyleSheet("font-family: 'Segoe UI', 'Inter', 'Roboto', sans-serif; font-size: 12px; font-weight: bold; color: #818cf8;")
        info_layout.addWidget(self.total_label)
        info_layout.addWidget(self.unannotated_label)
        info_layout.addWidget(self.class_label)
        self.info_group.setLayout(info_layout)
        right_layout.addWidget(self.info_group)

        # Группа списка боксов
        self.list_group = QGroupBox(tr("Боксы"))
        list_layout = QVBoxLayout()
        list_layout.setContentsMargins(4, 8, 4, 8)
        list_layout.setSpacing(2)
        self.box_list = QListWidget()
        self.box_list.itemClicked.connect(self.on_box_list_click)
        self.box_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.box_list.customContextMenuRequested.connect(self.show_box_context_menu)
        list_layout.addWidget(self.box_list)
        self.list_group.setLayout(list_layout)
        right_layout.addWidget(self.list_group)

        splitter.addWidget(right_panel)
        splitter.setSizes([1050, 230])
        
        middle_layout.addWidget(splitter)
        layout.addLayout(middle_layout)

        self.splitter = splitter
        self.right_panel = right_panel

        # Переменные для управления автоскрытием
        self.panel_visible = True
        self.panel_hover_active = False
        self.panel_hide_timer = QTimer()
        self.panel_hide_timer.setSingleShot(True)
        self.panel_hide_timer.timeout.connect(self.hide_panel_safe)
        self.panel_show_timer = QTimer()
        self.panel_show_timer.setSingleShot(True)
        self.panel_show_timer.timeout.connect(self.show_panel_safe)

        self.panel_timer = QTimer()
        self.panel_timer.timeout.connect(self.check_panel)
        self.panel_timer.start(100)

        # Нижняя панель миниатюр
        self.thumb_bar = ThumbnailBar(main_widget, main_window=self)
        self.thumb_bar.image_selected.connect(self.load_image_by_name)
        layout.addWidget(self.thumb_bar)

    def retranslate_ui(self):
        """Обновляет все тексты в интерфейсе при смене языка."""
        self.setWindowTitle(tr("VisionForge - Инструмент разметки"))
        self.create_menus()
        
        # Обновляем правую панель
        self.mode_group.setTitle(tr("Режим"))
        self.main_radio.setText(tr("Основной"))
        self.auto_radio.setText(tr("Авто"))
        self.transfer_btn.setText(tr("→ В основной"))
        
        self.filter_group.setTitle(tr("Фильтр"))
        # Обновляем комбобокс фильтра (нужно пересоздать список или обновить "Все")
        self.update_filter_combo()
        
        self.classes_group.setTitle(tr("Классы"))
        self.add_group_btn.setText(tr("+ Группа"))
        self.expand_all_btn.setText(tr("Развернуть всё"))
        self.collapse_all_btn.setText(tr("Свернуть всё"))
        self.class_tree.setHeaderLabels([tr("Класс / Группа"), tr("Счётчик")])
        
        self.info_group.setTitle(tr("Информация"))
        # Обновляем метки в info_group
        total = len(self.filtered_images)
        unannotated = sum(1 for f in self.filtered_images if not self.current_project.get_annotations(f))
        self.total_label.setText(f"{tr('Всего')}: {total}")
        self.unannotated_label.setText(f"{tr('Неразмечено')}: {unannotated}")
        if hasattr(self.widget, 'current_class'):
            self.class_label.setText(f"{tr('Класс')}: {self.widget.current_class}")
        
        self.btn_box_mode.setToolTip(tr("Бокс (B)"))
        self.btn_poly_mode.setToolTip(tr("Полигон (P)"))
        self.btn_auto.setToolTip(tr("Авторазметка (A)"))
        self.btn_next_class.setToolTip(tr("След. класс (T)"))
        self.btn_classes.setText(tr("Редактировать список классов..."))
        self.btn_delete_image.setToolTip(tr("Удалить изобр. (Ctrl+D)"))
        self.btn_prev.setToolTip(tr("Предыдущее изображение"))
        self.btn_next.setToolTip(tr("Следующее изображение"))
        
        self.list_group.setTitle(tr("Боксы"))
        self.update_box_list() # Обновит имена в списке боксов
        
        self.status_label.setText(tr("Готов к работе"))

    # ---------- Вспомогательные методы для панели ----------
    def show_box_context_menu(self, pos):
        item = self.box_list.itemAt(pos)
        if not item:
            return
        menu = QMenu()
        delete_action = menu.addAction(tr("Удалить"))
        delete_action.triggered.connect(lambda: self.delete_box_from_list(item))
        menu.exec_(self.box_list.mapToGlobal(pos))

    def delete_box_from_list(self, item):
        idx = item.data(Qt.UserRole)
        if idx is not None and 0 <= idx < len(self.widget.boxes):
            self.widget.save_state_to_history()
            del self.widget.boxes[idx]
            self.widget.selected_idx = -1
            self.widget.selection_changed.emit(-1)
            self.widget.boxes_changed.emit()
            self.widget.update()

    def transfer_to_main(self):
        """Переносит текущее изображение из авто-проекта в основной проект.
        Если папки изображений разные — перемещает файл.
        Аннотации добавляются в основной JSON и удаляются из авто-JSON."""
        if self.current_mode != 'auto':
            return
        if not self.filtered_images:
            return
        img_name = self.filtered_images[self.current_index]
        src_boxes = self.auto_project.get_annotations(img_name)
        if not src_boxes:
            QMessageBox.information(self, tr("Перенос"), tr("Текущее изображение не имеет аннотаций."))
            return

        src_img_path = os.path.join(self.auto_project.images_dir, img_name)
        dst_img_path = os.path.join(self.main_project.images_dir, img_name)

        # Если папки изображений разные — перемещаем файл
        same_dir = os.path.normpath(self.auto_project.images_dir) == os.path.normpath(self.main_project.images_dir)
        if not same_dir:
            if not os.path.exists(dst_img_path):
                os.makedirs(os.path.dirname(dst_img_path), exist_ok=True)
                shutil.move(src_img_path, dst_img_path)
            elif os.path.exists(src_img_path):
                # Файл уже есть в основной папке, удаляем из авто
                os.remove(src_img_path)

        # Добавляем имя файла в список изображений основного проекта
        if img_name not in self.main_project.images_list:
            self.main_project.images_list.append(img_name)
            self.main_project.images_list.sort()

        # Добавляем аннотации в основной проект
        self.main_project.annotations[img_name] = src_boxes
        self.main_project.image_types[img_name] = set(b['class'] for b in src_boxes)

        # Обновляем общий список классов основного проекта
        all_classes = set()
        for types in self.main_project.image_types.values():
            all_classes.update(types)
        self.main_project.classes = sorted(all_classes)
        self.main_project.generate_class_colors()
        self.main_project.clean_class_colors()
        self.main_project.save()

        # Удаляем аннотации из авто-проекта
        if img_name in self.auto_project.annotations:
            del self.auto_project.annotations[img_name]
        if img_name in self.auto_project.image_types:
            del self.auto_project.image_types[img_name]
        if not same_dir and img_name in self.auto_project.images_list:
            self.auto_project.images_list.remove(img_name)
        self.auto_project.save()

        QMessageBox.information(self, tr("Перенос"), f"{img_name} {tr('перенесено в основной проект.')}")

        # Обновляем список и переключаемся
        self.update_filtered_images()
        if self.current_index >= len(self.filtered_images):
            self.current_index = max(0, len(self.filtered_images) - 1)
        self.load_current_image()

    def prepare_dataset(self):
        dialog = PrepareDatasetDialog(self, self)
        dialog.exec_()

    # ---------- Управление автоскрытием панели ----------
    def show_panel_safe(self):
        if self.auto_hide_panel and self.right_panel.isHidden() and not self.panel_visible:
            self.right_panel.show()
            self.panel_visible = True

    def on_class_deleted_from_tree(self, class_name):
        self.delete_class(class_name)
    def hide_panel_safe(self):
        if self.auto_hide_panel and self.right_panel.isVisible() and self.panel_visible:
            if not self.right_panel.underMouse():
                self.right_panel.hide()
                self.panel_visible = False

    def check_panel(self):
        if not self.auto_hide_panel:
            return

        cursor_global = QCursor.pos()
        cursor_window = self.mapFromGlobal(cursor_global)

        if not self.rect().contains(cursor_window):
            return

        right_edge = self.width()
        margin = 50

        if cursor_window.x() >= right_edge - margin:
            if not self.panel_show_timer.isActive() and not self.panel_visible:
                self.panel_show_timer.start(150)
        else:
            if self.panel_show_timer.isActive():
                self.panel_show_timer.stop()

            if self.panel_visible and not self.right_panel.underMouse():
                if not self.panel_hide_timer.isActive():
                    self.panel_hide_timer.start(500)
            else:
                if self.panel_hide_timer.isActive():
                    self.panel_hide_timer.stop()

    # ---------- Управление иерархией классов ----------
    def add_class_group(self):
        name, ok = QInputDialog.getText(self, tr("Новая группа"), tr("Введите название группы:"))
        if ok and name.strip():
            self.current_project.class_hierarchy.append({"name": name.strip(), "children": []})
            self.update_class_tree()
            self.on_hierarchy_changed()

    def show_statistics(self):
        dialog = StatisticsDialog(self.current_project, self)
        dialog.exec_()

    def on_hierarchy_changed(self):
        self.current_project.class_hierarchy = self.class_tree.export_to_hierarchy()
        self.current_project.update_classes_from_hierarchy()
        self.current_project.save()
        self.update_filter_combo()

    def update_class_tree(self):
        if not hasattr(self, 'class_tree'):
            return
        counts = {}
        if self.filtered_images:
            img_name = self.filtered_images[self.current_index]
            boxes = self.current_project.get_annotations(img_name)
            for box in boxes:
                cls = box.get('class', 'unknown')
                counts[cls] = counts.get(cls, 0) + 1
        self.class_tree.populate_from_hierarchy(
            self.current_project.class_hierarchy,
            self.current_project.class_colors,
            counts
        )

    # ---------- Переключение режимов ----------
    def switch_to_training_mode(self):
        self.central_stack.setCurrentWidget(self.training_widget)

    def switch_to_annotation_mode(self):
        self.central_stack.setCurrentWidget(self.annotation_container)

    # ---------- Методы меню ----------
    def save_project(self):
        self.current_project.save()
        self.update_status(tr("Проект сохранён"))

    def save_project_as(self):
        new_path, _ = QFileDialog.getSaveFileName(self, tr("Сохранить копию JSON как"), "", tr("JSON files (*.json)"))
        if new_path:
            # Bug #2 fix: save full format (annotations + colors + hierarchy)
            data = {
                "annotations": self.current_project.annotations,
                "class_colors": self.current_project.class_colors,
                "class_hierarchy": self.current_project.class_hierarchy,
                "last_image": self.current_project.last_image,
            }
            with open(new_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self.update_status(f"{tr('Копия сохранена в')} {new_path}")

    def export_yolo(self):
        from project.exporters import export_yolo
        output_dir = QFileDialog.getExistingDirectory(self, tr("Выберите папку для экспорта YOLO"))
        if output_dir:
            export_yolo(self.current_project, output_dir)

    def export_coco(self):
        from project.exporters import export_coco
        output_file, _ = QFileDialog.getSaveFileName(self, tr("Сохранить COCO JSON"), "", tr("JSON files (*.json)"))
        if output_file:
            export_coco(self.current_project, output_file)

    def export_voc(self):
        from project.exporters import export_voc
        output_dir = QFileDialog.getExistingDirectory(self, tr("Выберите папку для экспорта Pascal VOC"))
        if output_dir:
            export_voc(self.current_project, output_dir)

    def batch_process(self):
        if self.detector is None:
            reply = QMessageBox.question(self, tr("Модель не загружена"),
                                         tr("Детектор не загружен. Хотите открыть настройки и указать путь к модели?"),
                                         QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.open_settings()
            return

        dlg = BatchDialog(self)
        if dlg.exec_() != QDialog.Accepted:
            return

        params = dlg.get_params()

        # Определяем список изображений
        if params["source_type"] == "project":
            images = self.current_project.images_list.copy()
            source_dir = self.current_project.images_dir
        else:
            folder = params["source_path"]
            if not folder or not os.path.isdir(folder):
                QMessageBox.warning(self, tr("Ошибка"), tr("Укажите существующую папку с изображениями."))
                return
            # Получаем все файлы с подходящими расширениями
            valid_exts = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff')
            images = [f for f in os.listdir(folder) if f.lower().endswith(valid_exts)]
            source_dir = folder
            if not images:
                QMessageBox.information(self, tr("Пакетная разметка"), tr("В указанной папке нет изображений."))
                return

        if not images:
            QMessageBox.information(self, tr("Пакетная разметка"), tr("Нет изображений для обработки."))
            return

        progress_dlg = ProgressDialog(len(images), self)
        progress_dlg.cancelled.connect(self.on_batch_cancelled)

        self.batch_worker = BatchWorker(images, self.current_project, self.detector, self.classifier, params,
                                        source_dir)
        self.batch_worker.auto_project = self.auto_project
        self.batch_worker.progress.connect(progress_dlg.update_progress)
        self.batch_worker.finished.connect(lambda success, msg: self.on_batch_finished(success, msg, progress_dlg))
        self.batch_worker.start()

        progress_dlg.exec_()

    def on_batch_cancelled(self):
        if hasattr(self, 'batch_worker') and self.batch_worker.isRunning():
            self.batch_worker.cancel()

    def on_batch_finished(self, success, message, progress_dlg):
        progress_dlg.close()
        if success:
            self.auto_project.save()
            self.auto_project.load()
            self.update_status(message)
            QMessageBox.information(self, tr("Пакетная разметка"), message)
        else:
            QMessageBox.critical(self, tr("Ошибка"), message)

    def show_help(self):
        help_text = tr("Горячие клавиши") + ":\n\n" + \
                    "N - " + tr("начать рисование бокса") + "\n" + \
                    "S - " + tr("сохранить изменения") + "\n" + \
                    "E - " + tr("изменить класс выбранного бокса на текущий") + "\n" + \
                    "T - " + tr("переключить текущий класс на следующий") + "\n" + \
                    "D - " + tr("удалить выбранный бокс") + "\n" + \
                    "Ctrl+D - " + tr("удалить текущее изображение") + "\n" + \
                    "F - " + tr("предыдущее изображение") + "\n" + \
                    "G - " + tr("следующее изображение") + "\n" + \
                    "Ctrl+Z - " + tr("отменить последнее действие") + "\n" + \
                    "A - " + tr("авторазметка") + "\n" + \
                    "F11 - " + tr("полноэкранный режим (скрывает правую панель при включённой настройке)")

        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(tr("Справка"))
        msg_box.setText(help_text)
        msg_box.setStyleSheet(get_current_theme_style())
        msg_box.exec_()

    def show_about(self):
        about_text = "VisionForge\n\n" + \
                     tr("Версия") + " {}\n\n".format(VERSION) + \
                     tr("Инструмент для разметки изображений, детекции в реальном времени и обучения моделей YOLO.\nРазработано с использованием PyQt5, OpenCV, Ultralytics YOLO.")
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(tr("О программе"))
        msg_box.setText(about_text)
        msg_box.setStyleSheet(get_current_theme_style())
        msg_box.exec_()

    # ---------- Загрузка моделей ----------
    def load_models_from_config(self):
        self.detector = None
        self.classifier = None
        if os.path.exists(config.DETECTOR_PATH):
            try:
                self.detector = YOLO(config.DETECTOR_PATH)
                print(tr("Детектор загружен"))
            except Exception as e:
                print(f"{tr('Ошибка загрузки детектора')}: {e}")
        else:
            print(f"{tr('Детектор не найден')}: {config.DETECTOR_PATH}")

        if os.path.exists(config.CLASSIFIER_PATH):
            try:
                self.classifier = YOLO(config.CLASSIFIER_PATH)
                print(tr("Классификатор загружен"))
            except Exception as e:
                print(f"{tr('Ошибка загрузки классификатора')}: {e}")
        else:
            print(f"{tr('Классификатор не найден')}: {config.CLASSIFIER_PATH}")

        if hasattr(self, 'widget') and self.widget is not None:
            self.widget.set_models(self.detector, self.classifier)

    # ---------- Фильтрация и навигация ----------
    def update_filter_combo(self):
        self.filter_combo.blockSignals(True)
        current_text = self.filter_combo.currentText()
        self.filter_combo.clear()
        self.filter_combo.addItem(tr("Все"))
        self.filter_combo.addItems(self.current_project.classes)
        idx = self.filter_combo.findText(current_text)
        if idx >= 0:
            self.filter_combo.setCurrentIndex(idx)
        else:
            self.filter_combo.setCurrentIndex(0)
        self.filter_combo.blockSignals(False)

    def on_filter_changed(self, filter_text):
        self.filter_type = filter_text
        self.update_filtered_images()
        self.current_index = 0
        self.load_current_image()
        self.thumb_bar.clear()
        for f in self.filtered_images:
            self.thumb_bar.add_item(f)
        self.thumb_bar.load_visible_thumbnails()

    def update_filtered_images(self):
        if self.filter_type == tr("Все"):
            self.filtered_images = self.current_project.images_list.copy()
        else:
            self.filtered_images = [
                img for img in self.current_project.images_list
                if self.filter_type in self.current_project.image_types.get(img, set())
            ]
        self.total_label.setText(f"{tr('Всего')}: {len(self.filtered_images)}")
        # Bug #10 fix: an image is unannotated if it has no annotations OR an empty list
        unannotated = sum(
            1 for img in self.filtered_images
            if not self.current_project.annotations.get(img)
        )
        annotated = len(self.filtered_images) - unannotated
        self.unannotated_label.setText(f"{tr('Неразмечено')}: {unannotated}")
        
        self.progress_bar.setMaximum(len(self.filtered_images))
        self.progress_bar.setValue(annotated)
        
        if self.filtered_images:
            current_display_idx = self.current_index + 1 if self.current_index >= 0 else 0
            self.progress_bar.setFormat(f"{current_display_idx} / {len(self.filtered_images)}")
        else:
            self.progress_bar.setFormat("0 / 0")

    @property
    def image_types(self):
        return self.current_project.image_types

    def is_image_annotated(self, filename):
        return filename in self.current_project.annotations

    def load_current_image(self):
        if not self.filtered_images or self.current_index < 0 or self.current_index >= len(self.filtered_images):
            return
            
        if len(self.filtered_images) > 0:
            current_display_idx = self.current_index + 1
            self.progress_bar.setFormat(f"{current_display_idx} / {len(self.filtered_images)}")
            
        img_name = self.filtered_images[self.current_index]
        img_path = os.path.join(self.current_project.images_dir, img_name)
        if not os.path.exists(img_path):
            return
        img = cv2.imread(img_path)
        if img is None:
            return
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        self.widget.set_image(img_rgb)
        boxes = self.current_project.get_annotations(img_name)
        self.widget.set_boxes(boxes)
        self.widget.class_colors = self.current_project.class_colors
        # Сохраняем текущий выбранный класс (если он есть в списке классов проекта)
        keep_class = self.widget.current_class
        if keep_class not in self.current_project.classes:
            keep_class = self.current_project.classes[0] if self.current_project.classes else tr("unknown")
        self.widget.set_classes(self.current_project.classes, keep_class)
        self.update_box_list()
        self.update_class_tree()
        # Подсвечиваем текущее изображение в карусели
        self.thumb_bar.set_current(img_name)

    def load_image_by_name(self, filename):
        try:
            idx = self.filtered_images.index(filename)
        except ValueError:
            return
        self.current_index = idx
        self.load_current_image()

    def next_image(self):
        if self.current_index < len(self.filtered_images) - 1:
            self.current_index += 1
            self.load_current_image()

    def prev_image(self):
        if self.current_index > 0:
            self.current_index -= 1
            self.load_current_image()

    # ---------- Обработка изменений боксов ----------
    def on_boxes_changed(self):
        if self.filtered_images:
            img_name = self.filtered_images[self.current_index]
            if img_name in self.thumb_memory_cache:
                del self.thumb_memory_cache[img_name]
            cache_path = self.get_thumbnail_cache_path(img_name)
            if cache_path and os.path.exists(cache_path):
                os.remove(cache_path)
            self.current_project.set_annotations(img_name, self.widget.boxes)
            self.current_project.save()
            self.thumb_bar.load_visible_thumbnails()
            self.update_box_list()
            self.update_class_tree()
            self.update_filter_combo()
            self.update_filtered_images()

    def update_box_list(self):
        self.box_list.clear()
        for i, box in enumerate(self.widget.boxes):
            class_name = box.get('class', 'unknown')
            text = f"{i}: {class_name}"
            item = QListWidgetItem()
            item.setData(Qt.UserRole, i)
            item.setSizeHint(QSize(100, 28))
            self.box_list.addItem(item)
            box_widget = BoxItemWidget(text, i)
            box_widget.delete_clicked.connect(self.delete_box_by_index)
            self.box_list.setItemWidget(item, box_widget)
            if i == self.widget.selected_idx:
                item.setSelected(True)

    def delete_box_by_index(self, index):
        if 0 <= index < len(self.widget.boxes):
            self.widget.save_state_to_history()
            del self.widget.boxes[index]
            self.widget.selected_idx = -1
            self.widget.selection_changed.emit(-1)
            self.widget.boxes_changed.emit()
            self.widget.update()

    def on_selection_changed(self, idx):
        self.box_list.setCurrentRow(idx)

    def on_box_list_click(self, item):
        idx = item.data(Qt.UserRole)
        self.widget.selected_idx = idx
        self.widget.update()

    def update_status(self, msg):
        self.status_label.setText(msg)

    # ---------- Управление классами ----------
    def open_type_dialog(self):
        dialog = TypeDialog(self.current_project, self.widget.current_class, self)
        if dialog.exec_() == QDialog.Accepted:
            self.update_class_tree()
            # Если пользователь выбрал класс в диалоге — применяем его
            selected_class = dialog.result_class or self.widget.current_class
            if selected_class not in self.current_project.classes:
                selected_class = self.current_project.classes[0] if self.current_project.classes else tr("unknown")
            self.widget.set_classes(self.current_project.classes, selected_class)
            self.class_label.setText(f"{tr('Класс')}: {selected_class}")
            self.update_filter_combo()
            self.current_project.save()

    def on_class_selected_from_list(self, class_name):
        self.widget.current_class = class_name
        self.class_label.setText(f"{tr('Класс')}: {class_name}")

    def on_class_color_changed(self, class_name):
        color = QColorDialog.getColor(QColor(self.current_project.class_colors.get(class_name, "#ffffff")),
                                      self, f"{tr('Выберите цвет для класса')} {class_name}")
        if color.isValid():
            self.current_project.class_colors[class_name] = color.name()
            self.widget.class_colors = self.current_project.class_colors
            self.current_project.save()
            self.update_class_tree()
            self.widget.update()

    def next_class(self):
        classes = self.current_project.classes
        if not classes:
            return
        try:
            idx = classes.index(self.widget.current_class)
        except ValueError:
            idx = 0
        idx = (idx + 1) % len(classes)
        self.widget.current_class = classes[idx]
        self.class_label.setText(f"{tr('Класс')}: {self.widget.current_class}")

    def delete_class(self, class_name):
        msg = QMessageBox(self)
        msg.setWindowTitle(f"{tr('Удалить класс')} '{class_name}'?")
        msg.setText(f"{tr('Что делать с объектами класса')} '{class_name}'?")
        delete_btn = msg.addButton(tr("Удалить все"), QMessageBox.ActionRole)
        reassign_btn = msg.addButton(tr("Переназначить"), QMessageBox.ActionRole)
        cancel_btn = msg.addButton(tr("Отмена"), QMessageBox.RejectRole)
        msg.exec_()

        if msg.clickedButton() == delete_btn:
            for img in list(self.current_project.annotations.keys()):
                boxes = self.current_project.annotations[img]
                new_boxes = [box for box in boxes if box["class"] != class_name]
                if new_boxes:
                    self.current_project.annotations[img] = new_boxes
                else:
                    del self.current_project.annotations[img]
            # Удаляем класс из иерархии
            self._remove_class_from_hierarchy(self.current_project.class_hierarchy, class_name)
            self.update_status(f"{tr('Класс')} '{class_name}' {tr('и все его боксы удалены.')}")

        elif msg.clickedButton() == reassign_btn:
            new_class, ok = QInputDialog.getItem(self, tr("Переназначить класс"),
                                                 tr("Выберите новый класс:"),
                                                 self.current_project.classes, 0, False)
            if ok and new_class and new_class != class_name:
                for img in self.current_project.annotations:
                    for box in self.current_project.annotations[img]:
                        if box["class"] == class_name:
                            box["class"] = new_class
                # Удаляем старый класс из иерархии
                self._remove_class_from_hierarchy(self.current_project.class_hierarchy, class_name)
                self.update_status(f"{tr('Класс')} '{class_name}' {tr('переназначен на')} '{new_class}'.")
            else:
                return False
        else:
            return False

        # Обновляем списки классов и цвета
        self.current_project.update_classes_from_hierarchy()
        self.current_project.generate_class_colors()
        self.current_project.clean_class_colors()
        self.current_project.save()

        # Обновляем интерфейс
        self.update_class_tree()
        self.widget.set_classes(self.current_project.classes, self.widget.current_class)
        self.update_filtered_images()
        self.load_current_image()
        self.thumb_bar.clear()
        for f in self.filtered_images:
            self.thumb_bar.add_item(f)
        self.thumb_bar.load_visible_thumbnails()
        self.update_filter_combo()
        return True

    def _remove_class_from_hierarchy(self, hierarchy, class_name):
        """Рекурсивно удаляет все вхождения class_name из иерархии."""
        i = 0
        while i < len(hierarchy):
            item = hierarchy[i]
            if isinstance(item, str):
                if item == class_name:
                    del hierarchy[i]
                    continue
            elif isinstance(item, dict) and "name" in item:
                if "children" in item:
                    self._remove_class_from_hierarchy(item["children"], class_name)
            i += 1
    # ---------- Авторазметка ----------
    def auto_annotate(self):
        if self.detector is None:
            reply = QMessageBox.question(self, tr("Модель не загружена"),
                                         tr("Детектор не загружен. Хотите открыть настройки и указать путь к модели?"),
                                         QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.open_settings()
            return
        self.widget.auto_annotate(cls_conf=config.CLS_CONF)

    # ---------- Операции с изображениями ----------
    def delete_current_image(self):
        if not self.filtered_images:
            return
        img_name = self.filtered_images[self.current_index]
        reply = QMessageBox.question(self, tr("Удалить"), f"{tr('Удалить')} {img_name}?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            file_path = os.path.join(self.current_project.images_dir, img_name)
            try:
                os.remove(file_path)
            except Exception as e:
                QMessageBox.critical(self, tr("Ошибка"), str(e))
                return
            if img_name in self.current_project.annotations:
                del self.current_project.annotations[img_name]
            if img_name in self.current_project.image_types:
                del self.current_project.image_types[img_name]
            self.current_project.images_list.remove(img_name)
            self.update_filtered_images()
            if self.current_index >= len(self.filtered_images):
                self.current_index = max(0, len(self.filtered_images) - 1)
            self.load_current_image()
            if img_name in self.thumb_memory_cache:
                del self.thumb_memory_cache[img_name]
            cache_path = self.get_thumbnail_cache_path(img_name)
            if cache_path and os.path.exists(cache_path):
                os.remove(cache_path)
            self.thumb_bar.clear()
            for f in self.filtered_images:
                self.thumb_bar.add_item(f)
            self.thumb_bar.load_visible_thumbnails()
            self.update_filter_combo()

    def load_folder(self):
        folder = QFileDialog.getExistingDirectory(self, tr("Выберите папку с изображениями"))
        if not folder:
            return
        ann_file = os.path.join(folder, "annotations.json")
        project = Project(folder, ann_file)
        ok, msg = self.safe_load_project(project)
        if not ok:
            reply = QMessageBox.critical(self, tr("Ошибка загрузки"),
                                         f"{tr('Не удалось загрузить проект из папки')}:\n{msg}\n\n{tr('Создать новый проект?')}",
                                         QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                self._reset_project(project)
            else:
                return
        self.current_project = project
        self.after_project_load()

    # ---------- Переключение режимов (main/auto) ----------
    def on_mode_changed(self):
        if self.main_radio.isChecked() and self.current_mode != 'main':
            self.switch_mode()
        elif self.auto_radio.isChecked() and self.current_mode != 'auto':
            self.switch_mode()
        self.transfer_btn.setEnabled(self.current_mode == 'auto')

    def switch_mode(self):
        self.current_project.save()
        if self.current_mode == 'main':
            self.current_mode = 'auto'
            self.current_project = self.auto_project
        else:
            self.current_mode = 'main'
            self.current_project = self.main_project
        # Bug #11 fix: blockSignals BEFORE after_project_load to prevent re-entrant on_mode_changed
        self.main_radio.blockSignals(True)
        self.auto_radio.blockSignals(True)
        self.main_radio.setChecked(self.current_mode == 'main')
        self.auto_radio.setChecked(self.current_mode == 'auto')
        self.main_radio.blockSignals(False)
        self.auto_radio.blockSignals(False)
        ok, msg = self.safe_load_project(self.current_project)
        if not ok:
            QMessageBox.warning(self, tr("Предупреждение"),
                                f"{tr('Не удалось загрузить проект в режиме')} {self.current_mode}:\n{msg}\n{tr('Будет создан новый проект.')}")
            self._reset_project(self.current_project)
        self.after_project_load()

    # ---------- Настройки ----------
    def open_settings(self):
        old_lang = config.LANGUAGE
        dialog = SettingsDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            new_config = dialog.get_config()
            config.save_config(new_config)
            # Обновляем константы модуля config
            config.DETECTOR_PATH = new_config["detector_path"]
            config.CLASSIFIER_PATH = new_config["classifier_path"]
            config.CLS_CONF = new_config["cls_conf"]
            config.SCREENSHOTS_DIR = new_config["main_images_dir"]
            config.MAIN_JSON = new_config["main_json"]
            config.AUTO_IMAGES_DIR = new_config.get("auto_images_dir", "") or config.SCREENSHOTS_DIR
            config.AUTO_JSON = new_config["auto_json"]
            config.THUMBNAIL_CACHE = new_config["thumbnail_cache"]
            config.THUMBNAIL_QUALITY = new_config["thumbnail_quality"]
            config.ASYNC_IMAGE_LOADING = new_config["async_image_loading"]
            config.AUTO_HIDE_PANEL = new_config["auto_hide_panel"]
            config.THEME = new_config["theme"]
            config.LANGUAGE = new_config.get("language", "ru")

            # Применяем новый язык
            from core.i18n import load_language
            load_language(config.LANGUAGE)

            # Применяем новую тему к главному окну
            self.setStyleSheet(get_current_theme_style())

            self.auto_hide_panel = new_config["auto_hide_panel"]

            self.load_models_from_config()
            self.main_project = Project(config.SCREENSHOTS_DIR, config.MAIN_JSON)
            self.auto_project = Project(config.AUTO_IMAGES_DIR, config.AUTO_JSON)
            
            # Проверка смены языка
            if config.LANGUAGE != old_lang:
                msg = QMessageBox(self)
                msg.setIcon(QMessageBox.Information)
                msg.setWindowTitle(tr("Смена языка"))
                msg.setText(tr("Для полной смены языка требуется перезагрузка программы."))
                restart_btn = msg.addButton(tr("Перезагрузить сейчас"), QMessageBox.ActionRole)
                msg.addButton(tr("Позже"), QMessageBox.RejectRole)
                msg.exec_()
                
                if msg.clickedButton() == restart_btn:
                    # Сохраняем проект перед перезагрузкой
                    self.current_project.save()
                    # Перезапуск
                    python = sys.executable
                    os.execl(python, python, *sys.argv)

            # Bug #12 fix: update current_project BEFORE calling save/load
            if self.current_mode == 'main':
                self.current_project = self.main_project
            else:
                self.current_project = self.auto_project
            self.current_project.save()
            self.current_project.load()
            self.update_filter_combo()
            self.update_filtered_images()
            self.load_current_image()
            self.thumb_bar.clear()
            for f in self.filtered_images:
                self.thumb_bar.add_item(f)
            self.thumb_bar.load_visible_thumbnails()

    # ---------- Миниатюры ----------
    def get_thumbnail_cache_path(self, filename):
        if not config.THUMBNAIL_CACHE:
            return None
        # Bug #7 fix: include images_dir to avoid collisions across projects
        key = f"{self.current_project.images_dir}|{filename}"
        hash_name = hashlib.md5(key.encode('utf-8')).hexdigest() + ".jpg"
        cache_dir = os.path.join(
            os.environ.get('LOCALAPPDATA', os.path.expanduser('~')),
            'VisionForge', 'thumb_cache'
        )
        os.makedirs(cache_dir, exist_ok=True)
        return os.path.join(cache_dir, hash_name)

    def generate_thumbnail(self, filename):
        if filename in self.thumb_memory_cache:
            return self.thumb_memory_cache[filename]

        path = os.path.join(self.current_project.images_dir, filename)
        from PyQt5.QtGui import QImageReader
        reader = QImageReader(path)
        reader.setAutoTransform(True)
        image = reader.read()
        if image.isNull():
            pixmap = QPixmap(140, 90)
            pixmap.fill(Qt.darkGray)
        else:
            pixmap = QPixmap.fromImage(image)
            pixmap = pixmap.scaled(140, 90, Qt.KeepAspectRatio, Qt.SmoothTransformation)

            boxes = self.current_project.get_annotations(filename)
            if boxes:
                painter = QPainter(pixmap)
                painter.setPen(QPen(QColor(0, 255, 0), 2))
                painter.setBrush(Qt.NoBrush)
                orig_w = image.width()
                orig_h = image.height()
                scale_w = pixmap.width() / orig_w
                scale_h = pixmap.height() / orig_h
                for box in boxes:
                    # Bug #4 fix: support polygon-only annotations (no bbox)
                    if "bbox" in box:
                        x1, y1, x2, y2 = box["bbox"]
                    elif "polygon" in box and box["polygon"]:
                        xs = [p[0] for p in box["polygon"]]
                        ys = [p[1] for p in box["polygon"]]
                        x1, y1, x2, y2 = min(xs), min(ys), max(xs), max(ys)
                    else:
                        continue
                    nx1 = int(x1 * scale_w)
                    ny1 = int(y1 * scale_h)
                    nx2 = int(x2 * scale_w)
                    ny2 = int(y2 * scale_h)
                    if nx2 <= nx1 or ny2 <= ny1:
                        continue
                    painter.drawRect(nx1, ny1, nx2 - nx1, ny2 - ny1)
                painter.end()

        self.thumb_memory_cache[filename] = pixmap

        cache_path = self.get_thumbnail_cache_path(filename)
        if cache_path:
            pixmap.save(cache_path, "JPG", quality=config.THUMBNAIL_QUALITY)

        return pixmap

    def load_thumbnail_disk(self, filename):
        if filename in self.thumb_memory_cache:
            return self.thumb_memory_cache[filename]

        cache_path = self.get_thumbnail_cache_path(filename)
        if cache_path and os.path.exists(cache_path):
            pixmap = QPixmap(cache_path)
            if not pixmap.isNull():
                self.thumb_memory_cache[filename] = pixmap
                return pixmap

        return self.generate_thumbnail(filename)

    # ---------- Горячие клавиши ----------
    def keyPressEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            if event.key() == Qt.Key_Z:
                self.widget.undo()
                return
            elif event.key() == Qt.Key_D:
                self.delete_current_image()
                return
            elif event.key() == Qt.Key_Q:
                self.close()
                return

        text = event.text().lower()
        if text == 'n':
            # N — принудительно начать рисовать в текущем режиме (бокс или полигон)
            self.force_start_drawing()
        elif text == 'b':
            self.set_box_mode()
        elif text == 'p':
            self.set_poly_mode()
        elif text == 's':
            self.on_boxes_changed()
        elif text == 'e':
            self.edit_selected()
        elif text == 't':
            self.next_class()
        elif text == 'd':
            self.widget.delete_selected()
        elif text == 'a':
            self.auto_annotate()
        elif text == 'f':
            self.prev_image()
        elif text == 'g':
            self.next_image()
        elif event.key() == Qt.Key_F11:
            if self.isFullScreen():
                self.showNormal()
                if self.right_panel.isHidden():
                    self.right_panel.show()
                    self.panel_visible = True
            else:
                self.showFullScreen()
                if self.auto_hide_panel and self.right_panel.isVisible():
                    self.right_panel.hide()
                    self.panel_visible = False
        else:
            super().keyPressEvent(event)

    def edit_selected(self):
        if 0 <= self.widget.selected_idx < len(self.widget.boxes):
            self.widget.boxes[self.widget.selected_idx]["class"] = self.widget.current_class
            self.widget.update()
            self.widget.boxes_changed.emit()
            self.update_class_tree()

    # ---------- Детекция ----------
    def start_overlay(self):
        if self.detector is None:
            reply = QMessageBox.question(self, tr("Модель не загружена"),
                                         tr("Детектор не загружен. Хотите открыть настройки и указать путь к модели?"),
                                         QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.open_settings()
            return
        from detection.overlay import OverlayWindow
        self.overlay = OverlayWindow(detector=self.detector, classifier=self.classifier)
        self.overlay.show()

    # ---------- Новый проект ----------
    def new_project(self):
        folder = QFileDialog.getExistingDirectory(self, tr("Выберите папку с изображениями"))
        if not folder:
            return
        default_json = os.path.join(folder, "annotations.json")
        json_path, _ = QFileDialog.getSaveFileName(self, tr("Сохранить JSON как"), default_json, "JSON files (*.json)")
        if not json_path:
            return

        project = Project(folder, json_path)

        if os.path.exists(json_path):
            ok, msg = self.safe_load_project(project)
            if ok:
                self.current_project = project
            else:
                reply = QMessageBox.question(self, tr("Файл существует"),
                                             f"{tr('Файл аннотаций уже существует, но повреждён')}:\n{msg}\n\n{tr('Перезаписать его новым проектом?')}",
                                             QMessageBox.Yes | QMessageBox.No)
                if reply == QMessageBox.Yes:
                    self._reset_project(project)
                    self.current_project = project
                else:
                    return
        else:
            self._reset_project(project)
            self.current_project = project

        self.after_project_load()

    def show_project_hub(self):
        from ui.project_hub_dialog import ProjectHubDialog
        dlg = ProjectHubDialog(self)
        if dlg.exec_() == QDialog.Accepted:
            if dlg.action_type == 'new':
                self.new_project()
            elif dlg.action_type == 'browse':
                self.load_project_from_json(dlg.selected_json_path)
            elif dlg.action_type == 'open_recent':
                self.load_project_from_json(dlg.selected_json_path)

    def load_project_from_json(self, json_path):
        folder = os.path.dirname(json_path)
        project = Project(folder, json_path)

        ok, msg = self.safe_load_project(project)
        if not ok:
            reply = QMessageBox.critical(self, tr("Ошибка загрузки"),
                                         f"{tr('Не удалось загрузить проект')}:\n{msg}\n\n{tr('Создать новый проект в этой папке?')}",
                                         QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                self._reset_project(project)
            else:
                return

        self.current_project = project
        self.after_project_load()
        
    def open_project(self):
        self.show_project_hub()

    # ---------- Импорт аннотаций ----------
    def import_annotations(self):
        from ui.import_dialog import ImportDialog
        dlg = ImportDialog(self)
        if dlg.exec_() == QDialog.Accepted:
            data, classes = dlg.result_data
            if dlg.add_radio.isChecked():
                # Добавить к текущему проекту
                for filename, boxes in data.items():
                    if filename in self.current_project.annotations:
                        self.current_project.annotations[filename].extend(boxes)
                    else:
                        self.current_project.annotations[filename] = boxes
                    # обновляем image_types для этого файла
                    classes_in_img = set(b['class'] for b in boxes)
                    self.current_project.image_types[filename] = classes_in_img.union(
                        self.current_project.image_types.get(filename, set())
                    )
                # пересчитываем общий список классов
                all_classes = set()
                for types in self.current_project.image_types.values():
                    all_classes.update(types)
                self.current_project.classes = sorted(all_classes)
                self.current_project.generate_class_colors()
                self.current_project.clean_class_colors()
                self.current_project.save()
                # обновляем интерфейс
                self.update_filter_combo()
                self.update_filtered_images()
                self.load_current_image()
                self.thumb_bar.clear()
                for f in self.filtered_images:
                    self.thumb_bar.add_item(f)
                self.thumb_bar.load_visible_thumbnails()
            else:
                # Создать новый проект
                folder = QFileDialog.getExistingDirectory(self, tr("Выберите папку для нового проекта (с изображениями)"))
                if not folder:
                    return
                default_json = os.path.join(folder, "annotations.json")
                json_path, _ = QFileDialog.getSaveFileName(self, tr("Сохранить JSON как"), default_json,
                                                           "JSON files (*.json)")
                if not json_path:
                    return
                project = Project(folder, json_path)
                project.annotations = data
                project.classes = classes
                project.images_list = list(data.keys())
                project.image_types = {img: set(box['class'] for box in boxes)
                                       for img, boxes in data.items()}
                project.generate_class_colors()
                project.save()
                self.current_project = project
                self.after_project_load()

    def closeEvent(self, event):
        if self.filtered_images and 0 <= self.current_index < len(self.filtered_images):
            self.current_project.last_image = self.filtered_images[self.current_index]
        if hasattr(self, 'current_project'):
            self.current_project.save()
        event.accept()

    def set_box_mode(self):
        self.widget.draw_mode = 'box'
        self.btn_box_mode.setChecked(True)
        self.btn_poly_mode.setChecked(False)
        # Принудительно обновляем визуальное состояние кнопок
        self.btn_box_mode.style().polish(self.btn_box_mode)
        self.btn_poly_mode.style().polish(self.btn_poly_mode)
        self.status_label.setText(tr("Режим: Прямоугольник"))

    def set_poly_mode(self):
        self.widget.draw_mode = 'polygon'
        self.btn_box_mode.setChecked(False)
        self.btn_poly_mode.setChecked(True)
        # Принудительно обновляем визуальное состояние кнопок
        self.btn_box_mode.style().polish(self.btn_box_mode)
        self.btn_poly_mode.style().polish(self.btn_poly_mode)
        self.status_label.setText(tr("Режим: Полигон"))

    def force_start_drawing(self):
        """Принудительно начинает рисование нового объекта в текущем режиме,
        даже если курсор находится внутри другого бокса/полигона."""
        if self.widget.draw_mode == 'polygon':
            self.widget.start_polygon_drawing()
        else:
            self.widget.start_drawing()
