# ui/statistics_dialog.py

import csv
from collections import Counter
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QFileDialog, QMessageBox, QTextEdit,
                             QGroupBox, QGridLayout, QTabWidget, QWidget)

from PyQt5.QtGui import QFont
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from ui.theme import get_current_theme_style
from core.i18n import tr

class StatisticsDialog(QDialog):
    def __init__(self, project, parent=None):
        super().__init__(parent)
        self.project = project
        self.setWindowTitle(tr("Статистика проекта"))
        self.setModal(True)
        self.setMinimumSize(900, 700)
        self.setStyleSheet(get_current_theme_style())

        layout = QVBoxLayout(self)

        tabs = QTabWidget()
        tabs.tabBar().setExpanding(False)
        layout.addWidget(tabs)

        # --- Вкладка "Общая статистика" ---
        general_tab = QWidget()
        general_layout = QVBoxLayout(general_tab)

        info_group = QGroupBox(tr("Общая информация"))
        info_layout = QGridLayout()

        total_images = len(self.project.images_list)
        annotated_images = sum(1 for f in self.project.images_list if f in self.project.annotations)
        total_boxes = sum(len(boxes) for boxes in self.project.annotations.values())
        unique_classes = len(self.project.classes)

        info_layout.addWidget(QLabel(tr("Всего изображений:")), 0, 0)
        info_layout.addWidget(QLabel(str(total_images)), 0, 1)
        info_layout.addWidget(QLabel(tr("Изображений с разметкой:")), 1, 0)
        info_layout.addWidget(QLabel(str(annotated_images)), 1, 1)
        info_layout.addWidget(QLabel(tr("Всего боксов:")), 2, 0)
        info_layout.addWidget(QLabel(str(total_boxes)), 2, 1)
        info_layout.addWidget(QLabel(tr("Уникальных классов:")), 3, 0)
        info_layout.addWidget(QLabel(str(unique_classes)), 3, 1)

        info_group.setLayout(info_layout)
        general_layout.addWidget(info_group)

        class_stats_group = QGroupBox(tr("Статистика по классам"))
        class_stats_layout = QVBoxLayout()

        self.class_stats_text = QTextEdit()
        self.class_stats_text.setReadOnly(True)
        self.class_stats_text.setFont(QFont("Courier New", 10))
        class_stats_layout.addWidget(self.class_stats_text)

        class_stats_group.setLayout(class_stats_layout)
        general_layout.addWidget(class_stats_group)

        tabs.addTab(general_tab, tr("Общая"))

        # --- Вкладка "Распределение классов" ---
        dist_tab = QWidget()
        dist_layout = QVBoxLayout(dist_tab)

        self.figure = Figure(figsize=(8, 5))
        self.canvas = FigureCanvas(self.figure)
        dist_layout.addWidget(self.canvas)

        tabs.addTab(dist_tab, tr("График"))

        # --- Вкладка "Рекомендации" ---
        rec_tab = QWidget()
        rec_layout = QVBoxLayout(rec_tab)

        self.rec_text = QTextEdit()
        self.rec_text.setReadOnly(True)
        self.rec_text.setFont(QFont("Arial", 11))
        rec_layout.addWidget(self.rec_text)

        tabs.addTab(rec_tab, tr("Рекомендации"))

        # Кнопка экспорта в CSV
        btn_layout = QHBoxLayout()
        self.export_btn = QPushButton(tr("Экспорт в CSV"))
        self.export_btn.clicked.connect(self.export_csv)
        btn_layout.addStretch()
        btn_layout.addWidget(self.export_btn)
        layout.addLayout(btn_layout)

        self.update_statistics()

    def update_statistics(self):
        box_counter = Counter()
        for boxes in self.project.annotations.values():
            for box in boxes:
                box_counter[box['class']] += 1

        # Формируем текст статистики по классам
        lines = []
        lines.append(f"{tr('Класс'):<25} | {tr('Количество'):<10} | {tr('Процент'):<8}")
        lines.append("-" * 50)
        
        total_boxes = sum(box_counter.values())
        for cls_name in sorted(self.project.classes):
            cnt = box_counter.get(cls_name, 0)
            percent = (cnt / total_boxes * 100) if total_boxes > 0 else 0
            lines.append(f"{cls_name:<25} | {cnt:<10} | {percent:>7.1f}%")
        
        self.class_stats_text.setText("\n".join(lines))

        # Обновляем график
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        if box_counter:
            labels = list(box_counter.keys())
            values = list(box_counter.values())
            ax.bar(labels, values, color='#2e7d32')
            ax.set_title(tr("Распределение классов"), color='white')
            ax.set_xlabel(tr("Класс"), color='white')
            ax.set_ylabel(tr("Количество боксов"), color='white')
            ax.tick_params(colors='white')
            # Поворачиваем метки если их много
            if len(labels) > 5:
                ax.set_xticklabels(labels, rotation=45, ha='right')
        else:
            ax.text(0.5, 0.5, tr("Нет данных для отображения"), 
                   ha='center', va='center', color='white')
        
        self.figure.tight_layout()
        self.canvas.draw()

        # Рекомендации
        self.generate_recommendations(box_counter)

    def generate_recommendations(self, box_counter):
        recs = []
        total_boxes = sum(box_counter.values())
        
        if total_boxes == 0:
            recs.append(f"• {tr('Начните разметку изображений, чтобы получить рекомендации.')}")
        else:
            # Дисбаланс классов
            counts = list(box_counter.values())
            if counts:
                min_cnt = min(counts)
                max_cnt = max(counts)
                if max_cnt > min_cnt * 3:
                    recs.append(f"• {tr('Обнаружен значительный дисбаланс классов. Рекомендуется добавить больше примеров для редких классов.')}")
            
            # Мало данных
            for cls_name, cnt in box_counter.items():
                if cnt < 50:
                    recs.append(f"• {tr('Для класса')} '{cls_name}' {tr('собрано менее 50 примеров. Этого может быть недостаточно для качественного обучения.')}")

            # Рекомендация по аугментации
            if total_boxes < 1000:
                recs.append(f"• {tr('Общий объем данных невелик. Используйте более агрессивную аугментацию при обучении.')}")

        if not recs:
            recs.append(f"• {tr('Датасет выглядит сбалансированным. Продолжайте в том же духе!')}")

        self.rec_text.setText("\n\n".join(recs))

    def export_csv(self):
        filename, _ = QFileDialog.getSaveFileName(self, tr("Сохранить статистику"), "", "CSV Files (*.csv)")
        if filename:
            try:
                box_counter = Counter()
                for boxes in self.project.annotations.values():
                    for box in boxes:
                        box_counter[box['class']] += 1

                with open(filename, 'w', encoding='utf-8', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow([tr("Класс"), tr("Количество"), tr("Процент")])
                    total_boxes = sum(box_counter.values())
                    for cls_name in sorted(self.project.classes):
                        cnt = box_counter.get(cls_name, 0)
                        percent = (cnt / total_boxes * 100) if total_boxes > 0 else 0
                        writer.writerow([cls_name, cnt, f"{percent:.2f}%"])
                
                QMessageBox.information(self, tr("Экспорт завершен"), tr("Статистика успешно экспортирована в CSV"))
            except Exception as e:
                QMessageBox.critical(self, tr("Ошибка"), f"{tr('Не удалось экспортировать данные')}: {str(e)}")