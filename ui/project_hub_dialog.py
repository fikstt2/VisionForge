import os
import time
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QListWidget, QListWidgetItem, QWidget,
                             QFileDialog, QInputDialog, QMessageBox)
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import Qt, QSize
from core.i18n import tr
import config

class ProjectHubDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("VisionForge - Хаб проектов"))
        self.setMinimumSize(800, 560)
        
        self.selected_json_path = None
        self.action_type = None  # 'open_recent', 'browse', 'new'
        
        self.init_ui()
        self.load_recent_projects()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Header
        header = QLabel(tr("Добро пожаловать в VisionForge"))
        header.setStyleSheet("font-size: 24px; font-weight: bold;")
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)
        
        subtitle = QLabel(tr("Выберите недавний проект или создайте новый"))
        subtitle.setStyleSheet("font-size: 14px; color: #aaa;")
        subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle)
        
        # List
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("""
            QListWidget {
                border: 1px solid #3f3f46;
                border-radius: 8px;
                background-color: #27272a;
            }
            QListWidget::item {
                border-bottom: 1px solid #3f3f46;
                padding: 5px;
            }
            QListWidget::item:selected {
                background-color: #4f46e5;
            }
        """)
        self.list_widget.itemDoubleClicked.connect(self.on_item_double_clicked)
        layout.addWidget(self.list_widget)
        
        # Bottom Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)
        
        self.btn_new = QPushButton(tr("Создать новый проект"))
        self.btn_new.setMinimumHeight(40)
        self.btn_new.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.btn_new.clicked.connect(self.on_new_project)
        
        self.btn_browse = QPushButton(tr("Обзор..."))
        self.btn_browse.setMinimumHeight(40)
        self.btn_browse.setStyleSheet("font-size: 14px;")
        self.btn_browse.clicked.connect(self.on_browse)
        
        self.btn_close = QPushButton(tr("Закрыть"))
        self.btn_close.setMinimumHeight(40)
        self.btn_close.clicked.connect(self.reject)
        
        btn_layout.addWidget(self.btn_new)
        btn_layout.addWidget(self.btn_browse)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_close)
        
        layout.addLayout(btn_layout)
        
    def load_recent_projects(self):
        self.list_widget.clear()
        recent = config.get_recent_projects()
        
        if not recent:
            item = QListWidgetItem()
            item.setFlags(Qt.NoItemFlags)
            
            w = QLabel(tr("Нет недавних проектов."))
            w.setAlignment(Qt.AlignCenter)
            w.setStyleSheet("color: #777; font-size: 14px; padding: 20px;")
            
            item.setSizeHint(w.sizeHint())
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, w)
            return

        for proj in recent:
            item = QListWidgetItem(self.list_widget)
            widget = self.create_project_widget(proj, item)
            item.setSizeHint(widget.sizeHint())
            self.list_widget.setItemWidget(item, widget)
            item.setData(Qt.UserRole, proj.get("json_path"))
            
    def create_project_widget(self, proj, item):
        w = QWidget()
        layout = QHBoxLayout(w)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Thumbnail
        thumb_label = QLabel()
        thumb_label.setFixedSize(80, 80)
        thumb_label.setStyleSheet("background-color: #18181b; border-radius: 6px;")
        thumb_label.setAlignment(Qt.AlignCenter)
        
        thumb_path = proj.get("thumbnail", "")
        if thumb_path and os.path.exists(thumb_path):
            pixmap = QPixmap(thumb_path)
            if not pixmap.isNull():
                thumb_label.setPixmap(pixmap.scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else:
                thumb_label.setText("IMG")
        else:
            thumb_label.setText("NO IMG")
            
        layout.addWidget(thumb_label)
        
        # Info
        info_layout = QVBoxLayout()
        
        name = proj.get("name", "Project")
        name_label = QLabel(name)
        name_label.setStyleSheet("font-size: 16px; font-weight: bold; color: white;")
        info_layout.addWidget(name_label)
        
        path_label = QLabel(proj.get("json_path", ""))
        path_label.setStyleSheet("font-size: 12px; color: #aaa;")
        info_layout.addWidget(path_label)
        
        desc = proj.get("description", "")
        desc_label = QLabel(desc if desc else tr("Нет описания"))
        desc_label.setStyleSheet("font-size: 13px; color: #ccc; font-style: italic;")
        info_layout.addWidget(desc_label)
        
        info_layout.addStretch()
        layout.addLayout(info_layout)
        
        # Actions
        action_layout = QVBoxLayout()
        
        btn_open = QPushButton(tr("Открыть"))
        btn_open.clicked.connect(lambda _, p=proj.get("json_path"): self.open_project_path(p))
        
        btn_edit = QPushButton(tr("Описание..."))
        btn_edit.clicked.connect(lambda _, p=proj.get("json_path"), d=desc: self.edit_description(p, d))
        
        action_layout.addWidget(btn_open)
        action_layout.addWidget(btn_edit)
        action_layout.addStretch()
        
        layout.addLayout(action_layout)
        return w
        
    def edit_description(self, json_path, current_desc):
        text, ok = QInputDialog.getText(self, tr("Редактировать описание"), 
                                        tr("Введите новое описание проекта:"), 
                                        text=current_desc)
        if ok:
            config.update_recent_project_description(json_path, text)
            self.load_recent_projects()
            
    def open_project_path(self, path):
        if not os.path.exists(path):
            QMessageBox.warning(self, tr("Ошибка"), f"{tr('Файл не найден:')}\n{path}")
            return
            
        self.selected_json_path = path
        self.action_type = 'open_recent'
        self.accept()
        
    def on_item_double_clicked(self, item):
        path = item.data(Qt.UserRole)
        if path:
            self.open_project_path(path)
            
    def on_browse(self):
        json_path, _ = QFileDialog.getOpenFileName(self, tr("Выберите файл аннотаций JSON"), "", "JSON files (*.json)")
        if json_path:
            self.selected_json_path = json_path
            self.action_type = 'browse'
            self.accept()
            
    def on_new_project(self):
        self.action_type = 'new'
        self.accept()
