# core/gallery_dialog.py
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QListWidget, QListWidgetItem, QComboBox,
                             QPushButton)
from PyQt5.QtCore import Qt, QTimer, QSize
from PyQt5.QtGui import QIcon
from ui.theme import get_current_theme_style

class GalleryDialog(QDialog):
    def __init__(self, parent, filenames, classes, main_window):
        super().__init__(parent)
        self.setStyleSheet(get_current_theme_style())
        self.main_window = main_window
        self.filenames = filenames
        self.classes = classes
        self.setWindowTitle("Галерея")
        self.setModal(True)
        self.resize(900, 600)

        layout = QVBoxLayout(self)

        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Фильтр:"))
        self.filter_combo = QComboBox()
        self.filter_combo.addItem("Все")
        self.filter_combo.addItems(self.classes)
        self.filter_combo.addItem("Неразмеченные")
        self.filter_combo.currentTextChanged.connect(self.apply_filter)
        filter_layout.addWidget(self.filter_combo)
        layout.addLayout(filter_layout)

        self.list_widget = QListWidget()
        self.list_widget.setViewMode(QListWidget.IconMode)
        self.list_widget.setIconSize(QSize(120, 80))
        self.list_widget.setGridSize(QSize(130, 90))
        self.list_widget.setResizeMode(QListWidget.Adjust)
        self.list_widget.setSelectionMode(QListWidget.ExtendedSelection)
        self.list_widget.itemDoubleClicked.connect(self.accept)
        self.list_widget.setStyleSheet("background-color: #3c3c3c; border: none;")
        layout.addWidget(self.list_widget)

        self.scroll_timer = QTimer()
        self.scroll_timer.setSingleShot(True)
        self.scroll_timer.timeout.connect(self.load_visible_thumbnails)
        self.list_widget.verticalScrollBar().valueChanged.connect(self.on_scroll)

        btn_layout = QHBoxLayout()
        btn_ok = QPushButton("Выбрать")
        btn_ok.clicked.connect(self.accept)
        btn_cancel = QPushButton("Отмена")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)

        self.populate_list()

    def populate_list(self):
        self.list_widget.clear()
        for f in self.filenames:
            item = QListWidgetItem()
            item.setData(Qt.UserRole, f)
            item.setIcon(QIcon())
            item.setToolTip(f)
            item.setText("")
            self.list_widget.addItem(item)
        self.load_visible_thumbnails()

    def on_scroll(self):
        self.scroll_timer.start(100)

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

        start = max(0, start_idx - 2)
        end = min(list_widget.count(), end_idx + 3)

        for i in range(start, end):
            item = list_widget.item(i)
            if item.icon().isNull():
                filename = item.data(Qt.UserRole)
                pixmap = self.main_window.load_thumbnail_disk(filename)
                if pixmap:
                    item.setIcon(QIcon(pixmap))

        for i in range(list_widget.count()):
            if i < start or i >= end:
                item = list_widget.item(i)
                if not item.icon().isNull():
                    item.setIcon(QIcon())

    def apply_filter(self, filter_text):
        self.list_widget.clear()
        if filter_text == "Все":
            filtered = self.filenames
        elif filter_text == "Неразмеченные":
            filtered = [f for f in self.filenames if not self.main_window.is_image_annotated(f)]
        else:
            filtered = []
            for f in self.filenames:
                types = self.main_window.image_types.get(f, set())
                if filter_text in types:
                    filtered.append(f)
        for f in filtered:
            item = QListWidgetItem()
            item.setData(Qt.UserRole, f)
            item.setIcon(QIcon())
            item.setToolTip(f)
            item.setText("")
            self.list_widget.addItem(item)
        QTimer.singleShot(50, self.load_visible_thumbnails)

    def get_selected(self):
        items = self.list_widget.selectedItems()
        return [item.data(Qt.UserRole) for item in items]