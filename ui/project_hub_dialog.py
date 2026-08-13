# ui/project_hub_dialog.py
import os
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QListWidget, QListWidgetItem, QWidget,
                             QFileDialog, QInputDialog, QMessageBox)
from PyQt5.QtGui import QPixmap, QColor, QFont
from PyQt5.QtCore import Qt, QSize
from ui.theme import get_current_theme_style
from core.i18n import tr
import config

class ProjectHubDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("VisionForge — Хаб проектов"))
        self.setMinimumSize(850, 580)
        self.setStyleSheet(get_current_theme_style())
        
        self.selected_json_path = None
        self.action_type = None  # 'open_recent', 'browse', 'new'
        
        self.init_ui()
        self.load_recent_projects()
        
    def init_ui(self):
        # Главный горизонтальный разделитель: Левая панель действий и Правая панель недавних проектов
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # ================= ЛЕВАЯ ПАНЕЛЬ (Управление) =================
        left_panel = QWidget()
        left_panel.setFixedWidth(280)
        left_panel.setStyleSheet("background-color: #1e1e24; border-right: 1px solid #2d2d34;")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(24, 40, 24, 24)
        left_layout.setSpacing(16)
        
        # Логотип / Заголовок
        logo_label = QLabel("VisionForge")
        logo_label.setStyleSheet("font-size: 26px; font-weight: bold; color: #818cf8; font-family: 'Segoe UI', sans-serif;")
        logo_label.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(logo_label)
        
        desc_label = QLabel(tr("Умная разметка и подготовка данных"))
        desc_label.setStyleSheet("font-size: 11px; color: #71717a; margin-bottom: 20px;")
        desc_label.setWordWrap(True)
        desc_label.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(desc_label)
        
        # Кнопки действий
        btn_style = """
            QPushButton {
                background-color: #4f46e5;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 13px;
                font-weight: bold;
                padding: 12px;
            }
            QPushButton:hover { background-color: #6366f1; }
            QPushButton:pressed { background-color: #4338ca; }
        """
        
        self.btn_new = QPushButton(tr("✨ Создать новый проект"))
        self.btn_new.setStyleSheet(btn_style)
        self.btn_new.clicked.connect(self.on_new_project)
        left_layout.addWidget(self.btn_new)
        
        btn_secondary_style = """
            QPushButton {
                background-color: #27272a;
                color: #f4f4f5;
                border: 1px solid #3f3f46;
                border-radius: 8px;
                font-size: 13px;
                font-weight: 500;
                padding: 11px;
            }
            QPushButton:hover { background-color: #3f3f46; border-color: #52525b; }
            QPushButton:pressed { background-color: #18181b; }
        """
        
        self.btn_browse = QPushButton(tr("📂 Открыть файл проекта .vf"))
        self.btn_browse.setStyleSheet(btn_secondary_style)
        self.btn_browse.clicked.connect(self.on_browse)
        left_layout.addWidget(self.btn_browse)
        
        left_layout.addStretch()
        
        # Выход
        self.btn_close = QPushButton(tr("Закрыть"))
        self.btn_close.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #a1a1aa;
                border: 1px solid #27272a;
                border-radius: 6px;
                padding: 8px;
            }
            QPushButton:hover { color: #f4f4f5; background-color: #27272a; }
        """)
        self.btn_close.clicked.connect(self.reject)
        left_layout.addWidget(self.btn_close)
        
        main_layout.addWidget(left_panel)
        
        # ================= ПРАВАЯ ПАНЕЛЬ (Недавние проекты) =================
        right_panel = QWidget()
        right_panel.setStyleSheet("background-color: #121214;")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(30, 35, 30, 30)
        right_layout.setSpacing(15)
        
        recent_title = QLabel(tr("Недавние проекты"))
        recent_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #f4f4f5;")
        right_layout.addWidget(recent_title)
        
        # Список карточек
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("""
            QListWidget {
                border: none;
                background-color: transparent;
                outline: none;
            }
            QListWidget::item {
                background-color: #1e1e24;
                border: 1px solid #2d2d34;
                border-radius: 10px;
                margin-bottom: 10px;
                padding: 0px;
            }
            QListWidget::item:hover {
                background-color: #24242c;
                border-color: #4f46e5;
            }
            QListWidget::item:selected {
                background-color: #24242c;
                border-color: #6366f1;
            }
        """)
        self.list_widget.itemDoubleClicked.connect(self.on_item_double_clicked)
        right_layout.addWidget(self.list_widget)
        
        main_layout.addWidget(right_panel)
        
    def load_recent_projects(self):
        self.list_widget.clear()
        recent = config.get_recent_projects()  # всегда возвращает список словарей

        if not recent:
            item = QListWidgetItem()
            item.setFlags(Qt.NoItemFlags)
            w = QLabel(tr("Здесь будут отображаться ваши недавние проекты."))
            w.setAlignment(Qt.AlignCenter)
            w.setStyleSheet("color: #52525b; font-size: 13px; font-style: italic; padding: 40px;")
            item.setSizeHint(w.sizeHint())
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, w)
            return

        for proj in recent:
            if not isinstance(proj, dict):
                continue
            item = QListWidgetItem()
            widget = self.create_project_widget(proj, item)
            item.setSizeHint(widget.sizeHint())
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, widget)
            item.setData(Qt.UserRole, proj.get("json_path"))
            
    def create_project_widget(self, proj, item):
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        layout = QHBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(16)
        
        # Превью кадра (миниатюра)
        thumb_label = QLabel()
        thumb_label.setFixedSize(110, 75)
        thumb_label.setStyleSheet("background-color: #121214; border-radius: 6px; border: 1px solid #2d2d34;")
        thumb_label.setAlignment(Qt.AlignCenter)
        
        thumb_path = proj.get("thumbnail", "")
        if thumb_path and os.path.exists(thumb_path):
            pixmap = QPixmap(thumb_path)
            if not pixmap.isNull():
                thumb_label.setPixmap(pixmap.scaled(110, 75, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation))
            else:
                thumb_label.setText("Empty")
                thumb_label.setStyleSheet("color: #3f3f46; font-size: 10px;")
        else:
            thumb_label.setText("No Image")
            thumb_label.setStyleSheet("color: #3f3f46; font-size: 10px;")
            
        layout.addWidget(thumb_label)
        
        # Информационный блок
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)
        
        name = proj.get("name", "Project")
        name_label = QLabel(name)
        name_label.setStyleSheet("font-size: 15px; font-weight: bold; color: #f4f4f5;")
        info_layout.addWidget(name_label)
        
        path_label = QLabel(proj.get("json_path", ""))
        path_label.setStyleSheet("font-size: 11px; color: #71717a;")
        path_label.setWordWrap(False)
        info_layout.addWidget(path_label)
        
        desc = proj.get("description", "")
        desc_label = QLabel(desc if desc else tr("Без описания"))
        desc_label.setStyleSheet("font-size: 12px; color: #a1a1aa; font-style: italic;")
        info_layout.addWidget(desc_label)
        
        info_layout.addStretch()
        layout.addLayout(info_layout, 1)
        
        # Кнопки быстрых действий справа в карточке
        action_layout = QVBoxLayout()
        action_layout.setSpacing(6)
        
        btn_open = QPushButton(tr("Открыть"))
        btn_open.setFixedSize(90, 28)
        btn_open.setStyleSheet("""
            QPushButton {
                background-color: #27272a;
                color: #f4f4f5;
                border: 1px solid #3f3f46;
                border-radius: 5px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #4f46e5; border-color: #818cf8; color: white; }
        """)
        btn_open.clicked.connect(lambda _, p=proj.get("json_path"): self.open_project_path(p))
        
        btn_edit = QPushButton(tr("Заметка..."))
        btn_edit.setFixedSize(90, 28)
        btn_edit.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #71717a;
                border: 1px solid #2d2d34;
                border-radius: 5px;
                font-size: 11px;
            }
            QPushButton:hover { color: #e4e4e7; border-color: #3f3f46; background-color: #27272a; }
        """)
        btn_edit.clicked.connect(lambda _, p=proj.get("json_path"), d=desc: self.edit_description(p, d))
        
        action_layout.addWidget(btn_open)
        action_layout.addWidget(btn_edit)
        action_layout.addStretch()
        
        layout.addLayout(action_layout)
        return w
        
    def edit_description(self, json_path, current_desc):
        text, ok = QInputDialog.getText(self, tr("Описание проекта"), 
                                        tr("Введите краткое примечание к проекту:"), 
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
        json_path, _ = QFileDialog.getOpenFileName(self, tr("Выберите файл проекта VisionForge"), "", "VisionForge Project (*.vf);;JSON files (*.json)")
        if json_path:
            self.selected_json_path = json_path
            self.action_type = 'browse'
            self.accept()
            
    def on_new_project(self):
        self.action_type = 'new'
        self.accept()