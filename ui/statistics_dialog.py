# ui/statistics_dialog.py
import os
import csv
from collections import Counter
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QFileDialog, QMessageBox, QTextEdit,
                             QGroupBox, QGridLayout, QTabWidget, QWidget)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
import matplotlib
matplotlib.use('Qt5Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from ui.theme import DARK_STYLE

class StatisticsDialog(QDialog):
    def __init__(self, project, parent=None):
        super().__init__(parent)
        self.project = project
        self.setWindowTitle("Статистика проекта")
        self.setModal(True)
        self.setMinimumSize(900, 700)
        self.setStyleSheet(DARK_STYLE)

        layout = QVBoxLayout(self)

        # Вкладки: Общая статистика, Распределение классов, Рекомендации
        tabs = QTabWidget()
        layout.addWidget(tabs)

        # --- Вкладка "Общая статистика" ---
        general_tab = QWidget()
        general_layout = QVBoxLayout(general_tab)

        # Информационные поля
        info_group = QGroupBox("Общая информация")
        info_layout = QGridLayout()

        total_images = len(self.project.images_list)
        annotated_images = sum(1 for f in self.project.images_list if f in self.project.annotations)
        total_boxes = sum(len(boxes) for boxes in self.project.annotations.values())
        unique_classes = len(self.project.classes)

        info_layout.addWidget(QLabel("Всего изображений:"), 0, 0)
        info_layout.addWidget(QLabel(str(total_images)), 0, 1)
        info_layout.addWidget(QLabel("Изображений с разметкой:"), 1, 0)
        info_layout.addWidget(QLabel(str(annotated_images)), 1, 1)
        info_layout.addWidget(QLabel("Всего боксов:"), 2, 0)
        info_layout.addWidget(QLabel(str(total_boxes)), 2, 1)
        info_layout.addWidget(QLabel("Уникальных классов:"), 3, 0)
        info_layout.addWidget(QLabel(str(unique_classes)), 3, 1)

        info_group.setLayout(info_layout)
        general_layout.addWidget(info_group)

        # Таблица или текстовое поле с распределением по классам (для детального просмотра)
        class_stats_group = QGroupBox("Статистика по классам")
        class_stats_layout = QVBoxLayout()

        self.class_stats_text = QTextEdit()
        self.class_stats_text.setReadOnly(True)
        self.class_stats_text.setFont(QFont("Courier New", 10))
        class_stats_layout.addWidget(self.class_stats_text)

        class_stats_group.setLayout(class_stats_layout)
        general_layout.addWidget(class_stats_group)

        tabs.addTab(general_tab, "Общая")

        # --- Вкладка "Распределение классов" ---
        dist_tab = QWidget()
        dist_layout = QVBoxLayout(dist_tab)

        self.figure = Figure(figsize=(8, 5))
        self.canvas = FigureCanvas(self.figure)
        dist_layout.addWidget(self.canvas)

        tabs.addTab(dist_tab, "График")

        # --- Вкладка "Рекомендации" ---
        rec_tab = QWidget()
        rec_layout = QVBoxLayout(rec_tab)

        self.rec_text = QTextEdit()
        self.rec_text.setReadOnly(True)
        self.rec_text.setFont(QFont("Arial", 11))
        rec_layout.addWidget(self.rec_text)

        tabs.addTab(rec_tab, "Рекомендации")

        # Кнопка экспорта в CSV
        btn_layout = QHBoxLayout()
        self.export_btn = QPushButton("Экспорт в CSV")
        self.export_btn.clicked.connect(self.export_csv)
        btn_layout.addStretch()
        btn_layout.addWidget(self.export_btn)
        layout.addLayout(btn_layout)

        # Заполняем данные
        self.update_statistics()

    def update_statistics(self):
        """Вычисляет статистику и обновляет виджеты."""
        # Подсчёт количества боксов по классам
        box_counter = Counter()
        # Количество изображений, содержащих класс
        image_counter = Counter()

        for img_name, boxes in self.project.annotations.items():
            # Учёт классов на изображении (уникальные)
            classes_in_image = set()
            for box in boxes:
                cls = box.get('class', 'unknown')
                box_counter[cls] += 1
                classes_in_image.add(cls)
            for cls in classes_in_image:
                image_counter[cls] += 1

        # Формируем текстовую статистику
        lines = []
        lines.append(f"{'Класс':<20} {'Боксы':>10} {'Изображения':>15}")
        lines.append("-" * 50)
        for cls in sorted(self.project.classes):
            boxes = box_counter.get(cls, 0)
            images = image_counter.get(cls, 0)
            lines.append(f"{cls:<20} {boxes:>10} {images:>15}")
        self.class_stats_text.setText("\n".join(lines))

        # Построение гистограммы
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        classes = sorted(self.project.classes)
        box_counts = [box_counter.get(cls, 0) for cls in classes]

        ax.bar(classes, box_counts, color='#0d7377')
        ax.set_xlabel('Класс')
        ax.set_ylabel('Количество боксов')
        ax.set_title('Распределение классов')
        ax.tick_params(axis='x', rotation=45)
        self.figure.tight_layout()
        self.canvas.draw()

        # Рекомендации
        rec_lines = []
        total_boxes = sum(box_counter.values())
        if total_boxes == 0:
            rec_lines.append("Проект не содержит размеченных изображений.")
        else:
            # Минимальное рекомендуемое количество боксов для класса (например, 100)
            MIN_REC = 100
            for cls, count in box_counter.items():
                if count < MIN_REC:
                    rec_lines.append(f"⚠️ Класс '{cls}' содержит всего {count} боксов. Рекомендуется не менее {MIN_REC}.")
            # Дисбаланс: если максимальное количество боксов превышает минимальное более чем в 10 раз
            if box_counter:
                max_count = max(box_counter.values())
                min_count = min(box_counter.values())
                if max_count / min_count > 10:
                    rec_lines.append("⚠️ Сильный дисбаланс классов. Рекомендуется собрать больше данных для малочисленных классов или применить аугментацию.")

            # Рекомендация по разделению train/val/test
            if total_boxes > 0:
                rec_lines.append("")
                rec_lines.append("Рекомендуемое разбиение датасета:")
                rec_lines.append("- Train: 70-80%")
                rec_lines.append("- Validation: 10-20%")
                rec_lines.append("- Test: 10-20% (если нужно)")

            # Если есть классы без боксов (но они есть в списке классов) – странно, но проверим
            for cls in self.project.classes:
                if cls not in box_counter:
                    rec_lines.append(f"⚠️ Класс '{cls}' не встречается ни в одном боксе.")

        self.rec_text.setText("\n".join(rec_lines))

    def export_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "Сохранить статистику", "", "CSV files (*.csv)")
        if not path:
            return

        try:
            with open(path, 'w', newline='', encoding='utf-8-sig') as f:  # utf-8-sig добавляет BOM
                writer = csv.writer(f)
                writer.writerow(["Класс", "Количество боксов", "Количество изображений"])

                box_counter = Counter()
                image_counter = Counter()
                for img_name, boxes in self.project.annotations.items():
                    classes_in_image = set()
                    for box in boxes:
                        cls = box.get('class', 'unknown')
                        box_counter[cls] += 1
                        classes_in_image.add(cls)
                    for cls in classes_in_image:
                        image_counter[cls] += 1

                for cls in sorted(self.project.classes):
                    writer.writerow([cls, box_counter.get(cls, 0), image_counter.get(cls, 0)])

            QMessageBox.information(self, "Экспорт", f"Статистика сохранена в {path}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить файл:\n{str(e)}")