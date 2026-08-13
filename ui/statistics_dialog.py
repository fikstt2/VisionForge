# ui/statistics_dialog.py
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QGroupBox, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QPushButton)
from PyQt5.QtCore import Qt
from ui.theme import get_current_theme_style
from collections import defaultdict
from core.i18n import tr

class StatisticsDialog(QDialog):
    def __init__(self, project, parent=None):
        super().__init__(parent)
        self.project = project
        self.setWindowTitle(tr("Статистика проекта"))
        self.setMinimumSize(650, 500)
        self.setStyleSheet(get_current_theme_style())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # ===== Сбор метрик по монолитному ядру =====
        total_images = len(self.project.images_list)
        
        annotated_by_user = sum(1 for f in self.project.images_list if len(self.project.get_annotations(f, 'main')) > 0)
        annotated_by_ai = sum(1 for f in self.project.images_list if len(self.project.get_annotations(f, 'main')) == 0 and len(self.project.get_annotations(f, 'auto')) > 0)
        unannotated_images = total_images - annotated_by_user - annotated_by_ai

        # Считаем объекты раздельно по режимам
        class_main_counts = defaultdict(int)
        class_auto_counts = defaultdict(int)
        all_seen_classes = set(self.project.classes) # Базовые классы проекта

        total_main_objects = 0
        total_auto_objects = 0
        
        for f in self.project.images_list:
            # Ручная разметка
            for box in self.project.get_annotations(f, 'main'):
                cls = box.get('class', 'unknown')
                class_main_counts[cls] += 1
                all_seen_classes.add(cls)
                total_main_objects += 1
                
            # Авторазметка ИИ
            for box in self.project.get_annotations(f, 'auto'):
                cls = box.get('class', 'unknown')
                class_auto_counts[cls] += 1
                all_seen_classes.add(cls)
                total_auto_objects += 1

        # ===== Общая сводка =====
        summary_group = QGroupBox(tr("Сводка по изображениям"))
        summary_layout = QVBoxLayout(summary_group)
        summary_layout.setSpacing(6)

        summary_layout.addWidget(QLabel(f"{tr('Всего изображений в папке')}: <b>{total_images}</b>"))
        summary_layout.addWidget(QLabel(f"{tr('Утверждено вручную (Основной режим)')}: <b style='color: #4ade80;'>{annotated_by_user}</b> (Объектов: {total_main_objects})"))
        summary_layout.addWidget(QLabel(f"{tr('Размечено моделью (Ожидает проверки)')}: <b style='color: #60a5fa;'>{annotated_by_ai}</b> (Объектов: {total_auto_objects})"))
        summary_layout.addWidget(QLabel(f"{tr('Абсолютно неразмечено')}: <b style='color: #f87171;'>{unannotated_images}</b>"))
        summary_group.setLayout(summary_layout)
        layout.addWidget(summary_group)

        # ===== Детальная таблица распределения по классам =====
        class_group = QGroupBox(tr("Распределение объектов по классам"))
        class_layout = QVBoxLayout(class_group)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels([
            tr("Класс"), 
            tr("Вручную (Main)"), 
            tr("Моделью (Auto)"), 
            tr("Всего (Total)")
        ])
        
        # Настройка поведения колонок
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)

        # Подготовка данных для сортировки по общему числу объектов
        table_data = []
        for cls_name in all_seen_classes:
            m_count = class_main_counts[cls_name]
            a_count = class_auto_counts[cls_name]
            t_count = m_count + a_count
            # Чтобы пустые классы из схемы не захламляли верх, сортируем по total
            table_data.append((cls_name, m_count, a_count, t_count))
            
        # Сортируем: сначала те, где больше всего объектов
        table_data.sort(key=lambda x: x[3], reverse=True)

        self.table.setRowCount(len(table_data))
        
        for row, (cls_name, m_count, a_count, t_count) in enumerate(table_data):
            item_name = QTableWidgetItem(str(cls_name))
            item_main = QTableWidgetItem(str(m_count) if m_count > 0 else "-")
            item_auto = QTableWidgetItem(str(a_count) if a_count > 0 else "-")
            item_total = QTableWidgetItem(str(t_count))
            
            # Выравнивание по центру для цифр
            item_main.setTextAlignment(Qt.AlignCenter)
            item_auto.setTextAlignment(Qt.AlignCenter)
            item_total.setTextAlignment(Qt.AlignCenter)
            
            # Подсветим ручную разметку зеленым
            if m_count > 0:
                item_main.setForeground(Qt.GlobalColor.green)
                
            # ИСПРАВЛЕНО: Делаем тотал жирным через объект QFont
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
        close_btn.setFixedHeight(32)
        close_btn.setFixedWidth(100)
        close_btn.clicked.connect(self.accept)
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)