# core/gallery_dialog.py
import os

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QListWidget, QListWidgetItem, QComboBox,
                             QPushButton, QLineEdit, QAbstractItemView,
                             QWidget)
from PyQt5.QtCore import Qt, QTimer, QSize
from PyQt5.QtGui import QIcon, QColor
from ui.theme import get_current_theme_style
from core.i18n import tr


class GalleryDialog(QDialog):
    def __init__(self, parent, filenames, classes, main_window):
        super().__init__(parent)
        self.setStyleSheet(get_current_theme_style())
        self.main_window = main_window
        self.filenames = filenames
        self.classes = classes
        self.setWindowTitle(tr("Галерея"))
        self.setModal(True)
        self.resize(1100, 750)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # ===== Верхняя панель =====
        top_bar = QHBoxLayout()
        top_bar.setSpacing(10)

        # Заголовок
        title = QLabel(tr("Галерея изображений"))
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #f4f4f5;")
        top_bar.addWidget(title)

        top_bar.addStretch()

        # Счётчик
        self.count_label = QLabel()
        self.count_label.setStyleSheet("font-size: 12px; color: #71717a;")
        top_bar.addWidget(self.count_label)

        layout.addLayout(top_bar)

        # ===== Панель фильтров =====
        filter_bar = QHBoxLayout()
        filter_bar.setSpacing(10)

        # Поиск по имени
        search_icon_label = QLabel("🔍")
        search_icon_label.setStyleSheet("font-size: 14px;")
        filter_bar.addWidget(search_icon_label)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText(tr("Поиск по имени файла..."))
        self.search_edit.setFixedHeight(32)
        self.search_edit.setStyleSheet("""
            QLineEdit {
                background-color: #3f3f46;
                color: #f4f4f5;
                border: 1px solid #52525b;
                border-radius: 8px;
                padding: 4px 12px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 1px solid #818cf8;
            }
        """)
        self.search_edit.textChanged.connect(self._on_search_or_filter)
        filter_bar.addWidget(self.search_edit)

        # Фильтр по классу
        filter_label = QLabel(tr("Класс:"))
        filter_label.setStyleSheet("font-size: 12px; color: #a1a1aa;")
        filter_bar.addWidget(filter_label)

        self.filter_combo = QComboBox()
        self.filter_combo.setFixedHeight(32)
        self.filter_combo.addItem(tr("Все"))
        self.filter_combo.addItems(self.classes)
        self.filter_combo.addItem(tr("Неразмеченные"))
        self.filter_combo.currentTextChanged.connect(self._on_search_or_filter)
        filter_bar.addWidget(self.filter_combo)

        # Размер миниатюр
        size_label = QLabel(tr("Размер:"))
        size_label.setStyleSheet("font-size: 12px; color: #a1a1aa;")
        filter_bar.addWidget(size_label)

        self.size_combo = QComboBox()
        self.size_combo.setFixedHeight(32)
        self.size_combo.addItem(tr("Мелкие"), 80)
        self.size_combo.addItem(tr("Средние"), 140)
        self.size_combo.addItem(tr("Крупные"), 220)
        self.size_combo.setCurrentIndex(1)  # Средние по умолчанию
        self.size_combo.currentIndexChanged.connect(self._on_size_changed)
        filter_bar.addWidget(self.size_combo)

        layout.addLayout(filter_bar)

        # ===== Сетка изображений =====
        self.list_widget = QListWidget()
        self.list_widget.setViewMode(QListWidget.IconMode)
        self.list_widget.setIconSize(QSize(140, 100))
        self.list_widget.setGridSize(QSize(155, 120))
        self.list_widget.setResizeMode(QListWidget.Adjust)
        self.list_widget.setSelectionMode(QListWidget.ExtendedSelection)
        self.list_widget.itemDoubleClicked.connect(self.accept)
        self.list_widget.setStyleSheet("""
            QListWidget {
                background-color: #18181b;
                border: 1px solid #3f3f46;
                border-radius: 10px;
                padding: 8px;
                outline: none;
            }
            QListWidget::item {
                border: 2px solid transparent;
                border-radius: 8px;
                padding: 4px;
                margin: 2px;
                color: #a1a1aa;
                font-size: 10px;
            }
            QListWidget::item:selected {
                border: 2px solid #6366f1;
                background-color: rgba(99, 102, 241, 50);
            }
            QListWidget::item:hover:!selected {
                border: 2px solid #52525b;
                background-color: rgba(63, 63, 70, 100);
            }
        """)
        self.list_widget.setSpacing(4)
        layout.addWidget(self.list_widget)

        # Ленивая загрузка
        self.scroll_timer = QTimer()
        self.scroll_timer.setSingleShot(True)
        self.scroll_timer.timeout.connect(self.load_visible_thumbnails)
        self.list_widget.verticalScrollBar().valueChanged.connect(self._on_scroll)

        # ===== Нижняя панель кнопок =====
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        # Статус выбора
        self.selection_label = QLabel(tr("Ничего не выбрано"))
        self.selection_label.setStyleSheet("font-size: 12px; color: #71717a;")
        btn_layout.addWidget(self.selection_label)

        btn_layout.addStretch()

        btn_cancel = QPushButton(tr("Отмена"))
        btn_cancel.setFixedHeight(36)
        btn_cancel.setFixedWidth(100)
        btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #3f3f46;
                color: #d4d4d8;
                border: 1px solid #52525b;
                border-radius: 8px;
                font-size: 12px;
                font-weight: 500;
            }
            QPushButton:hover { background-color: #52525b; }
        """)
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        btn_ok = QPushButton(tr("Выбрать"))
        btn_ok.setFixedHeight(36)
        btn_ok.setFixedWidth(120)
        btn_ok.setStyleSheet("""
            QPushButton {
                background-color: #4f46e5;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #6366f1; }
        """)
        btn_ok.clicked.connect(self.accept)
        btn_layout.addWidget(btn_ok)

        layout.addLayout(btn_layout)

        # Обновляем счётчик выбранных
        self.list_widget.itemSelectionChanged.connect(self._update_selection_label)

        self.populate_list()

    def _on_size_changed(self, index):
        """Меняет размер миниатюр в сетке."""
        size = self.size_combo.currentData()
        aspect = 0.7  # высота = 70% ширины
        self.list_widget.setIconSize(QSize(size, int(size * aspect)))
        self.list_widget.setGridSize(QSize(size + 15, int(size * aspect) + 25))
        # Перезагружаем миниатюры
        QTimer.singleShot(50, self.load_visible_thumbnails)

    def _on_search_or_filter(self):
        """Объединённый обработчик поиска и фильтра."""
        search_text = self.search_edit.text().strip().lower()
        filter_text = self.filter_combo.currentText()

        # Шаг 1: фильтр по классу
        if filter_text == tr("Все"):
            filtered = list(self.filenames)
        elif filter_text == tr("Неразмеченные"):
            filtered = [f for f in self.filenames if not self.main_window.is_image_annotated(f)]
        else:
            filtered = []
            for f in self.filenames:
                types = self.main_window.image_types.get(f, set())
                if filter_text in types:
                    filtered.append(f)

        # Шаг 2: фильтр по поиску
        if search_text:
            filtered = [f for f in filtered if search_text in os.path.basename(f).lower()]

        self.list_widget.clear()
        for f in filtered:
            item = QListWidgetItem()
            item.setData(Qt.UserRole, f)
            item.setIcon(QIcon())
            item.setToolTip(os.path.basename(f))
            # Показываем имя файла под миниатюрой
            basename = os.path.splitext(os.path.basename(f))[0]
            if len(basename) > 18:
                basename = basename[:15] + "..."
            item.setText(basename)
            self.list_widget.addItem(item)

        self._update_count()
        QTimer.singleShot(50, self.load_visible_thumbnails)

    def populate_list(self):
        self.list_widget.clear()
        for f in self.filenames:
            item = QListWidgetItem()
            item.setData(Qt.UserRole, f)
            item.setIcon(QIcon())
            item.setToolTip(os.path.basename(f))
            basename = os.path.splitext(os.path.basename(f))[0]
            if len(basename) > 18:
                basename = basename[:15] + "..."
            item.setText(basename)
            self.list_widget.addItem(item)
        self._update_count()
        QTimer.singleShot(100, self.load_visible_thumbnails)

    def _update_count(self):
        total = self.list_widget.count()
        self.count_label.setText(f"{total} {tr('изображений')}")

    def _update_selection_label(self):
        count = len(self.list_widget.selectedItems())
        if count == 0:
            self.selection_label.setText(tr("Ничего не выбрано"))
        else:
            self.selection_label.setText(f"{tr('Выбрано')}: {count}")

    def _on_scroll(self):
        self.scroll_timer.start(80)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.scroll_timer.start(150)

    def load_visible_thumbnails(self):
        list_widget = self.list_widget
        if list_widget.count() == 0:
            return

        viewport_rect = list_widget.viewport().rect()
        start_idx = None
        end_idx = None

        for i in range(list_widget.count()):
            item_rect = list_widget.visualItemRect(list_widget.item(i))
            if item_rect.isEmpty():
                continue
            if item_rect.bottom() < viewport_rect.top():
                continue
            if item_rect.top() > viewport_rect.bottom():
                break
            if start_idx is None:
                start_idx = i
            end_idx = i

        if start_idx is None:
            return

        # Увеличенный буфер для плавного скролла
        buffer = 10
        start = max(0, start_idx - buffer)
        end = min(list_widget.count(), end_idx + buffer + 1)

        for i in range(start, end):
            item = list_widget.item(i)
            if item and item.icon().isNull():
                filename = item.data(Qt.UserRole)
                pixmap = self.main_window.load_thumbnail_disk(filename)
                if pixmap:
                    item.setIcon(QIcon(pixmap))

        # Выгружаем далёкие миниатюры для экономии памяти
        for i in range(list_widget.count()):
            if i < start or i >= end:
                item = list_widget.item(i)
                if item and not item.icon().isNull():
                    item.setIcon(QIcon())

    def get_selected(self):
        items = self.list_widget.selectedItems()
        return [item.data(Qt.UserRole) for item in items]