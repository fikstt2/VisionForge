# core/thumbnail_bar.py
import os

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QToolButton, QStyle, QListWidget, QListWidgetItem,
                             QListView, QDialog, QAbstractItemView)
from PyQt5.QtCore import Qt, QTimer, QSize, pyqtSignal
from PyQt5.QtGui import QIcon

class ThumbnailBar(QWidget):
    image_selected = pyqtSignal(str)

    def __init__(self, parent=None, main_window=None):
        super().__init__(parent)
        self.main_window = main_window
        self.setFixedHeight(130)
        self._current_filename = None

        from core.i18n import get_translator
        get_translator().languageChanged.connect(self.retranslate_ui)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self.content_widget = QWidget()
        self.content_widget.setStyleSheet("background: rgba(24, 24, 27, 220); border-top: 1px solid #3f3f46;")
        self.content_layout = QHBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(4, 4, 4, 4)
        self.content_layout.setSpacing(4)

        # Кнопка галереи
        self.folder_btn = QToolButton()
        self.folder_btn.setIcon(self.style().standardIcon(QStyle.SP_DirIcon))
        from core.i18n import tr
        self.folder_btn.setToolTip(tr("Открыть галерею"))
        self.folder_btn.clicked.connect(self.open_gallery)
        self.folder_btn.setFixedSize(28, 28)
        self.folder_btn.setStyleSheet("""
            QToolButton {
                background-color: #27272a;
                border: 1px solid #3f3f46;
                border-radius: 6px;
            }
            QToolButton:hover {
                background-color: #4f46e5;
                border-color: #818cf8;
            }
        """)
        self.content_layout.addWidget(self.folder_btn)

        # Кнопка «←» для прокрутки назад
        self.scroll_left_btn = QToolButton()
        self.scroll_left_btn.setText("<")
        self.scroll_left_btn.setFixedSize(20, 100)
        self.scroll_left_btn.setAutoRepeat(True)
        self.scroll_left_btn.setAutoRepeatInterval(50)
        self.scroll_left_btn.setStyleSheet("""
            QToolButton {
                background-color: rgba(32, 32, 38, 220);
                color: #a1a1aa;
                border: 1px solid #2e2e38;
                border-radius: 4px;
                font-size: 13px;
                font-weight: bold;
            }
            QToolButton:hover { background-color: #4f46e5; border-color: #818cf8; color: white; }
        """)
        self.scroll_left_btn.clicked.connect(self._scroll_left)
        self.content_layout.addWidget(self.scroll_left_btn)

        # Список миниатюр
        THUMB_W = 148
        THUMB_H = 102
        self.list_widget = QListWidget()
        self.list_widget.setViewMode(QListWidget.IconMode)
        self.list_widget.setFlow(QListWidget.LeftToRight)
        self.list_widget.setWrapping(False)
        # iconSize = gridSize: иконка заполняет всю ячейку — нет некликабельных зазоров
        self.list_widget.setIconSize(QSize(THUMB_W, THUMB_H))
        self.list_widget.setGridSize(QSize(THUMB_W + 4, THUMB_H + 4))
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list_widget.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list_widget.setResizeMode(QListWidget.Adjust)
        self.list_widget.setSelectionMode(QAbstractItemView.SingleSelection)
        self.list_widget.setSpacing(0)
        self.list_widget.setStyleSheet("""
            QListWidget {
                background: transparent;
                border: none;
                outline: none;
            }
            QListWidget::item {
                border: 2px solid transparent;
                border-radius: 6px;
                padding: 0px;
                margin: 1px;
            }
            QListWidget::item:selected {
                border: 2px solid #6366f1;
                background-color: rgba(99, 102, 241, 40);
            }
            QListWidget::item:hover:!selected {
                border: 2px solid #3f3f46;
                background-color: rgba(63, 63, 70, 80);
            }
        """)
        self.list_widget.setMovement(QListView.Static)
        self.list_widget.itemClicked.connect(self.on_item_clicked)
        self.list_widget.itemActivated.connect(self.on_item_clicked)
        self.list_widget.viewport().installEventFilter(self)
        self.content_layout.addWidget(self.list_widget)

        # Кнопка «→» для прокрутки вперёд
        self.scroll_right_btn = QToolButton()
        self.scroll_right_btn.setText(">")
        self.scroll_right_btn.setFixedSize(20, 100)
        self.scroll_right_btn.setAutoRepeat(True)
        self.scroll_right_btn.setAutoRepeatInterval(50)
        self.scroll_right_btn.setStyleSheet("""
            QToolButton {
                background-color: rgba(32, 32, 38, 220);
                color: #a1a1aa;
                border: 1px solid #2e2e38;
                border-radius: 4px;
                font-size: 13px;
                font-weight: bold;
            }
            QToolButton:hover { background-color: #4f46e5; border-color: #818cf8; color: white; }
        """)
        self.scroll_right_btn.clicked.connect(self._scroll_right)
        self.content_layout.addWidget(self.scroll_right_btn)

        self.main_layout.addWidget(self.content_widget)

        # Кнопка сворачивания
        self.collapse_btn = QPushButton("—")
        self.collapse_btn.setFixedHeight(12)
        self.collapse_btn.setStyleSheet("""
            QPushButton {
                background: #18181b;
                color: #52525b;
                border: none;
                border-top: 1px solid #27272a;
                font-weight: bold;
                font-size: 8px;
                padding: 0px;
            }
            QPushButton:hover {
                background: #27272a;
                color: #a1a1aa;
            }
        """)
        self.collapse_btn.clicked.connect(self.toggle_collapse)
        self.main_layout.addWidget(self.collapse_btn)

        self.is_collapsed = False

        # Таймер для отложенной загрузки при скролле
        self.scroll_timer = QTimer()
        self.scroll_timer.setSingleShot(True)
        self.scroll_timer.timeout.connect(self.load_visible_thumbnails)
        self.list_widget.horizontalScrollBar().valueChanged.connect(self._on_scroll)

        # Таймер начальной загрузки (при первом показе)
        self._initial_load_timer = QTimer()
        self._initial_load_timer.setSingleShot(True)
        self._initial_load_timer.timeout.connect(self.load_visible_thumbnails)

    def retranslate_ui(self):
        from core.i18n import tr
        self.folder_btn.setToolTip(tr("Открыть галерею"))

    def toggle_collapse(self):
        self.is_collapsed = not self.is_collapsed
        if self.is_collapsed:
            self.content_widget.hide()
            self.collapse_btn.setText("▼")
            self.setFixedHeight(14)
        else:
            self.content_widget.show()
            self.collapse_btn.setText("▲")
            self.setFixedHeight(130)
            QTimer.singleShot(50, self.load_visible_thumbnails)

    def _on_scroll(self):
        self.scroll_timer.start(80)

    def _scroll_left(self):
        sb = self.list_widget.horizontalScrollBar()
        sb.setValue(sb.value() - self.list_widget.gridSize().width())

    def _scroll_right(self):
        sb = self.list_widget.horizontalScrollBar()
        sb.setValue(sb.value() + self.list_widget.gridSize().width())

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        sb = self.list_widget.horizontalScrollBar()
        sb.setValue(sb.value() - delta)
        event.accept()
        self.scroll_timer.start(80)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if not self.is_collapsed:
            self.scroll_timer.start(150)

    def showEvent(self, event):
        super().showEvent(event)
        self._initial_load_timer.start(100)

    def load_visible_thumbnails(self):
        if self.main_window is None:
            return
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
            if item_rect.right() < viewport_rect.left():
                continue
            if item_rect.left() > viewport_rect.right():
                break
            if start_idx is None:
                start_idx = i
            end_idx = i

        if start_idx is None:
            return

        buffer = 5
        start = max(0, start_idx - buffer)
        end = min(list_widget.count(), end_idx + buffer + 1)

        for i in range(start, end):
            item = list_widget.item(i)
            if item and item.icon().isNull():
                filename = item.data(Qt.UserRole)
                pixmap = self.main_window.generate_thumbnail(filename)
                if pixmap:
                    item.setIcon(QIcon(pixmap))

        for i in range(list_widget.count()):
            if i < start or i >= end:
                item = list_widget.item(i)
                if item and not item.icon().isNull():
                    item.setIcon(QIcon())

    def add_item(self, filename):
        item = QListWidgetItem()
        item.setData(Qt.UserRole, filename)
        item.setIcon(QIcon())
        item.setToolTip(os.path.basename(filename))
        self.list_widget.addItem(item)

    def clear(self):
        self.list_widget.clear()
        self._current_filename = None

    def invalidate_item(self, filename):
        """Сбрасывает иконку элемента и немедленно перегенерирует миниатюру."""
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item and item.data(Qt.UserRole) == filename:
                item.setIcon(QIcon())  # сбрасываем — load_visible_thumbnails перерисует
                break
        self.load_visible_thumbnails()

    def set_current(self, filename):
        self._current_filename = filename
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.data(Qt.UserRole) == filename:
                self.list_widget.setCurrentItem(item)
                self.list_widget.scrollToItem(item, QAbstractItemView.PositionAtCenter)
                QTimer.singleShot(50, self.load_visible_thumbnails)
                return

    def open_gallery(self):
        if self.main_window is None:
            return
            
        # Адаптировано под новый монолитный формат проекта
        classes = self.main_window.project.classes
        filenames = self.main_window.filtered_images
        
        from core.gallery_dialog import GalleryDialog
        
        # Передаем self (parent) ПЕРВЫМ аргументом, затем список файлов и моделей
        dialog = GalleryDialog(self, filenames, classes, self.main_window)
        if dialog.exec_() == QDialog.Accepted:
            selected = dialog.get_selected()
            if selected:
                self.main_window.load_image_by_name(selected[0])

    def on_item_clicked(self, item):
        filename = item.data(Qt.UserRole)
        if filename:
            self.image_selected.emit(filename)

    def eventFilter(self, source, event):
        """Перехватываем клики на viewport карусели — любой пиксель ячейки кликабелен."""
        from PyQt5.QtCore import QEvent
        if source is self.list_widget.viewport() and event.type() == QEvent.MouseButtonPress:
            item = self.list_widget.itemAt(event.pos())
            if item is not None:
                self.list_widget.setCurrentItem(item)
                self.on_item_clicked(item)
                return True  # событие обработано, дальше не пропускаем
        return super().eventFilter(source, event)