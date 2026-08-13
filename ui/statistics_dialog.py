# ui/statistics_dialog.py
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QGroupBox, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QPushButton, QWidget, QFrame)
from PyQt5.QtGui import QFont, QColor
from PyQt5.QtCore import Qt
from ui.theme import get_current_theme_style
from collections import defaultdict
from core.i18n import tr

class StatisticsDialog(QDialog):
    def __init__(self, project, parent=None):
        super().__init__(parent)
        self.project = project
        self.setWindowTitle(tr("Статистика проекта"))
        self.setMinimumSize(700, 520)
        self.setStyleSheet(get_current_theme_style())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        # ===== Сбор метрик =====
        total_images = len(self.project.images_list)
        annotated_by_user = sum(1 for f in self.project.images_list if len(self.project.get_annotations(f, 'main')) > 0)
        annotated_by_ai = sum(1 for f in self.project.images_list if len(self.project.get_annotations(f, 'main')) == 0 and len(self.project.get_annotations(f, 'auto')) > 0)
        unannotated_images = total_images - annotated_by_user - annotated_by_ai

        class_main_counts = defaultdict(int)
        class_auto_counts = defaultdict(int)
        all_seen_classes = set(self.project.classes)

        total_main_objects = 0
        total_auto_objects = 0
        
        for f in self.project.images_list:
            for box in self.project.get_annotations(f, 'main'):
                cls = box.get('class', 'unknown')
                class_main_counts[cls] += 1
                all_seen_classes.add(cls)
                total_main_objects += 1
                
            for box in self.project.get_annotations(f, 'auto'):
                cls = box.get('class', 'unknown')
                class_auto_counts[cls] += 1
                all_seen_classes.add(cls)
                total_auto_objects += 1

        # ===== Карточки сводки =====
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(10)

        card_total = self.create_stat_card(tr("Всего кадров"), str(total_images), "#818cf8")
        card_main = self.create_stat_card(tr("Размечено вручную"), f"{annotated_by_user} ({total_main_objects} об.)", "#4ade80")
        card_auto = self.create_stat_card(tr("Размечено ИИ"), f"{annotated_by_ai} ({total_auto_objects} об.)", "#38bdf8")
        card_none = self.create_stat_card(tr("Не размечено"), str(unannotated_images), "#f87171" if unannotated_images > 0 else "#a1a1aa")

        cards_layout.addWidget(card_total)
        cards_layout.addWidget(card_main)
        cards_layout.addWidget(card_auto)
        cards_layout.addWidget(card_none)
        layout.addLayout(cards_layout)

        # ===== Детальная таблица распределения по классам =====
        class_group = QGroupBox(tr("Распределение объектов по классам"))
        class_layout = QVBoxLayout(class_group)
        class_layout.setContentsMargins(10, 14, 10, 10)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels([
            tr("Класс"), 
            tr("Вручную (Main)"), 
            tr("Моделью (Auto)"), 
            tr("Всего (Total)")
        ])
        
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)

        table_data = []
        for cls_name in all_seen_classes:
            m_count = class_main_counts[cls_name]
            a_count = class_auto_counts[cls_name]
            t_count = m_count + a_count
            table_data.append((cls_name, m_count, a_count, t_count))
            
        table_data.sort(key=lambda x: x[3], reverse=True)
        self.table.setRowCount(len(table_data))
        
        for row, (cls_name, m_count, a_count, t_count) in enumerate(table_data):
            item_name = QTableWidgetItem(str(cls_name))
            item_main = QTableWidgetItem(str(m_count) if m_count > 0 else "—")
            item_auto = QTableWidgetItem(str(a_count) if a_count > 0 else "—")
            item_total = QTableWidgetItem(str(t_count))
            
            item_main.setTextAlignment(Qt.AlignCenter)
            item_auto.setTextAlignment(Qt.AlignCenter)
            item_total.setTextAlignment(Qt.AlignCenter)
            
            font = item_total.font()
            font.setBold(True)
            item_total.setFont(font)

            self.table.setItem(row, 0, item_name)
            self.table.setItem(row, 1, item_main)
            self.table.setItem(row, 2, item_auto)
            self.table.setItem(row, 3, item_total)

        class_layout.addWidget(self.table)
        class_group.setLayout(class_layout)
        layout.addWidget(class_group)

        # Кнопка закрытия
        btn_layout = QHBoxLayout()
        close_btn = QPushButton(tr("Закрыть"))
        close_btn.setFixedHeight(30)
        close_btn.setFixedWidth(100)
        close_btn.clicked.connect(self.accept)
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

    def create_stat_card(self, title, value, accent_color):
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: #1a1a20;
                border: 1px solid #2e2e38;
                border-radius: 8px;
                padding: 6px;
            }}
        """)
        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(8, 8, 8, 8)
        c_layout.setSpacing(4)
        c_layout.setAlignment(Qt.AlignCenter)

        t_lbl = QLabel(title)
        t_lbl.setStyleSheet("color: #a1a1aa; font-size: 10px; font-weight: 500;")
        t_lbl.setAlignment(Qt.AlignCenter)

        v_lbl = QLabel(value)
        v_lbl.setStyleSheet(f"color: {accent_color}; font-size: 14px; font-weight: bold;")
        v_lbl.setAlignment(Qt.AlignCenter)

        c_layout.addWidget(t_lbl)
        c_layout.addWidget(v_lbl)
        return card