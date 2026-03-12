# core/thumbnail_bar.py
import os

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QToolButton, QStyle, QListWidget, QListWidgetItem,
                             QListView, QDialog)
from PyQt5.QtCore import Qt, QTimer, QSize, pyqtSignal
from PyQt5.QtGui import QIcon

class ThumbnailBar(QWidget):
    image_selected = pyqtSignal(str)

    def __init__(self, parent=None, main_window=None):
        super().__init__(parent)
        self.main_window = main_window
        self.setFixedHeight(120)
        self.setStyleSheet("background: rgba(43, 43, 43, 200);")

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self.content_widget = QWidget()
        self.content_layout = QHBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(2, 2, 2, 2)
        self.content_layout.setSpacing(2)

        self.folder_btn = QToolButton()
        self.folder_btn.setIcon(self.style().standardIcon(QStyle.SP_DirIcon))
        self.folder_btn.setToolTip("Открыть галерею")
        self.folder_btn.clicked.connect(self.open_gallery)
        self.folder_btn.setFixedSize(24, 24)
        self.content_layout.addWidget(self.folder_btn)

        self.list_widget = QListWidget()
        self.list_widget.setViewMode(QListWidget.IconMode)
        self.list_widget.setFlow(QListWidget.LeftToRight)
        self.list_widget.setWrapping(False)
        self.list_widget.setIconSize(QSize(140, 90))
        self.list_widget.setGridSize(QSize(150, 100))
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.list_widget.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list_widget.setResizeMode(QListWidget.Adjust)
        self.list_widget.setStyleSheet("background: transparent; border: none; font-size: 11px;")
        self.list_widget.setSpacing(2)
        self.list_widget.setMovement(QListView.Static)
        self.list_widget.itemClicked.connect(self.on_item_clicked)
        self.content_layout.addWidget(self.list_widget)

        self.main_layout.addWidget(self.content_widget)

        self.collapse_btn = QPushButton("▲")
        self.collapse_btn.setFixedHeight(12)
        self.collapse_btn.setStyleSheet("""
            QPushButton {
                background: rgba(60, 60, 60, 180);
                color: white;
                border: none;
                border-top: 1px solid #3c3c3c;
                font-weight: bold;
                font-size: 8px;
                padding: 0px;
            }
            QPushButton:hover {
                background: rgba(80, 80, 80, 200);
            }
        """)
        self.collapse_btn.clicked.connect(self.toggle_collapse)
        self.main_layout.addWidget(self.collapse_btn)

        self.is_collapsed = False

        self.scroll_timer = QTimer()
        self.scroll_timer.setSingleShot(True)
        self.scroll_timer.timeout.connect(self.load_visible_thumbnails)
        self.list_widget.horizontalScrollBar().valueChanged.connect(self.on_scroll)

    def toggle_collapse(self):
        self.is_collapsed = not self.is_collapsed
        if self.is_collapsed:
            self.content_widget.hide()
            self.collapse_btn.setText("▼")
            self.setFixedHeight(12)
        else:
            self.content_widget.show()
            self.collapse_btn.setText("▲")
            self.setFixedHeight(120)

    def on_scroll(self):
        self.scroll_timer.start(100)

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        self.list_widget.horizontalScrollBar().setValue(
            self.list_widget.horizontalScrollBar().value() - delta
        )
        event.accept()

    def load_visible_thumbnails(self):
        if self.main_window is None:
            return
        list_widget = self.list_widget
        scrollbar = list_widget.horizontalScrollBar()
        viewport_width = list_widget.viewport().width()
        item_width = list_widget.gridSize().width()
        if item_width == 0:
            return
        first = scrollbar.value() // item_width
        last = (scrollbar.value() + viewport_width) // item_width
        start = max(0, first - 2)
        end = min(list_widget.count(), last + 3)

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

    def add_item(self, filename):
        item = QListWidgetItem()
        item.setData(Qt.UserRole, filename)
        item.setIcon(QIcon())
        item.setToolTip(os.path.basename(filename))
        self.list_widget.addItem(item)

    def clear(self):
        self.list_widget.clear()

    def open_gallery(self):
        if self.main_window is None:
            return
        classes = self.main_window.current_project.classes
        filenames = [self.list_widget.item(i).data(Qt.UserRole) for i in range(self.list_widget.count())]
        from core.gallery_dialog import GalleryDialog
        dialog = GalleryDialog(self, filenames, classes, self.main_window)
        if dialog.exec_() == QDialog.Accepted:
            selected = dialog.get_selected()
            if selected:
                self.image_selected.emit(selected[0])

    def on_item_clicked(self, item):
        filename = item.data(Qt.UserRole)
        if filename:
            self.image_selected.emit(filename)