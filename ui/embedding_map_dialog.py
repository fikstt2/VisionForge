# ui/embedding_map_dialog.py
import os
import cv2
import numpy as np
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QComboBox, QCheckBox, QProgressBar, 
                             QGroupBox, QWidget, QSplitter, QScrollArea, QListWidget, QListWidgetItem)
from PyQt5.QtCore import Qt, QPointF, QRectF, pyqtSignal, QThread
from PyQt5.QtGui import QPainter, QPen, QColor, QBrush, QFont, QPixmap, QImage
from ui.theme import get_current_theme_style
from core.embedding_explorer import EmbeddingExplorer
from core.i18n import tr


class EmbeddingWorker(QThread):
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(dict)

    def __init__(self, project, method):
        super().__init__()
        self.project = project
        self.method = method

    def run(self):
        result = EmbeddingExplorer.analyze_project_embeddings(
            project=self.project,
            method=self.method,
            progress_callback=self.progress_signal.emit
        )
        self.finished_signal.emit(result)


class EmbeddingCanvas(QWidget):
    point_selected = pyqtSignal(str)  # filename
    point_double_clicked = pyqtSignal(str)  # filename

    def __init__(self, parent=None, project=None):
        super().__init__(parent)
        self.project = project
        self.points = []
        self.visible_classes = set()
        self.only_outliers = False

        self.zoom = 1.0
        self.offset_x = 0.0
        self.offset_y = 0.0
        self.last_mouse_pos = None

        self.hovered_point = None
        self.selected_point = None

        self.setMouseTracking(True)
        self.setMinimumSize(500, 400)
        self.setStyleSheet("background-color: #09090b;")

    def set_data(self, points, classes):
        self.points = points
        self.visible_classes = set(classes)
        self.hovered_point = None
        self.selected_point = None
        self.reset_view()
        self.update()

    def reset_view(self):
        self.zoom = 1.0
        self.offset_x = 0.0
        self.offset_y = 0.0

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        cx = w / 2.0 + self.offset_x
        cy = h / 2.0 + self.offset_y
        scale = min(w, h) * 0.42 * self.zoom

        # 1. Сетка координат
        painter.setPen(QPen(QColor(39, 39, 42), 1, Qt.DashLine))
        painter.drawLine(int(cx), 0, int(cx), h)
        painter.drawLine(0, int(cy), w, int(cy))

        # 2. Отрисовка точек
        for pt in self.points:
            cls_name = pt["class"]
            if cls_name not in self.visible_classes:
                continue
            if self.only_outliers and not pt["is_outlier"]:
                continue

            px = cx + pt["x"] * scale
            py = cy + pt["y"] * scale

            # Получаем цвет класса
            color_hex = "#4f46e5"
            if self.project and cls_name in self.project.class_colors:
                color_hex = self.project.class_colors[cls_name]
            base_color = QColor(color_hex)

            is_selected = (self.selected_point == pt["filename"])
            is_hovered = (self.hovered_point and self.hovered_point["filename"] == pt["filename"])

            # Аномалии: внешнее красное кольцо
            if pt["is_outlier"]:
                painter.setPen(QPen(QColor(239, 68, 68, 200), 2))
                painter.setBrush(Qt.NoBrush)
                painter.drawEllipse(QPointF(px, py), 10, 10)

            # Выбранная или наведенная точка
            if is_selected:
                painter.setPen(QPen(QColor(255, 255, 255), 2))
                painter.setBrush(QBrush(base_color))
                painter.drawEllipse(QPointF(px, py), 8, 8)
            elif is_hovered:
                painter.setPen(QPen(QColor(255, 255, 255, 180), 2))
                painter.setBrush(QBrush(base_color))
                painter.drawEllipse(QPointF(px, py), 7, 7)
            else:
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(base_color))
                painter.drawEllipse(QPointF(px, py), 5, 5)

        # 3. Всплывающая карточка предпросмотра при hover
        if self.hovered_point:
            self._draw_hover_card(painter, cx, cy, scale)

    def _draw_hover_card(self, painter, cx, cy, scale):
        pt = self.hovered_point
        px = cx + pt["x"] * scale
        py = cy + pt["y"] * scale

        card_w, card_h = 190, 60
        card_x = min(self.width() - card_w - 10, max(10, px + 12))
        card_y = min(self.height() - card_h - 10, max(10, py - card_h - 5))

        # Фон карточки
        painter.setPen(QPen(QColor(63, 63, 70), 1))
        painter.setBrush(QBrush(QColor(24, 24, 27, 240)))
        painter.drawRoundedRect(QRectF(card_x, card_y, card_w, card_h), 6, 6)

        # Текст карточки
        painter.setPen(QColor(244, 244, 245))
        font = QFont("Segoe UI", 9, QFont.Bold)
        painter.setFont(font)
        painter.drawText(int(card_x + 8), int(card_y + 18), pt["filename"])

        font_sub = QFont("Segoe UI", 8)
        painter.setFont(font_sub)
        painter.setPen(QColor(161, 161, 170))
        painter.drawText(int(card_x + 8), int(card_y + 34), f"{tr('Класс')}: {pt['class']}")

        if pt["is_outlier"]:
            painter.setPen(QColor(239, 68, 68))
            painter.drawText(int(card_x + 8), int(card_y + 50), f"⚠ {tr('Выброс / Аномалия')} (d={pt['score']})")
        else:
            painter.drawText(int(card_x + 8), int(card_y + 50), f"{tr('Боксов')}: {pt['box_count']}")

    def mouseMoveEvent(self, event):
        if event.buttons() & (Qt.LeftButton | Qt.RightButton):
            if self.last_mouse_pos is not None:
                dx = event.x() - self.last_mouse_pos.x()
                dy = event.y() - self.last_mouse_pos.y()
                self.offset_x += dx
                self.offset_y += dy
                self.last_mouse_pos = event.pos()
                self.update()
                return

        # Поиск точки под курсором
        w, h = self.width(), self.height()
        cx = w / 2.0 + self.offset_x
        cy = h / 2.0 + self.offset_y
        scale = min(w, h) * 0.42 * self.zoom

        mx, my = event.x(), event.y()
        found = None
        for pt in self.points:
            cls_name = pt["class"]
            if cls_name not in self.visible_classes:
                continue
            if self.only_outliers and not pt["is_outlier"]:
                continue

            px = cx + pt["x"] * scale
            py = cy + pt["y"] * scale
            dist = np.hypot(mx - px, my - py)
            if dist <= 10:
                found = pt
                break

        if found != self.hovered_point:
            self.hovered_point = found
            self.update()

    def mousePressEvent(self, event):
        self.last_mouse_pos = event.pos()
        if event.button() == Qt.LeftButton and self.hovered_point:
            self.selected_point = self.hovered_point["filename"]
            self.point_selected.emit(self.selected_point)
            self.update()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton and self.hovered_point:
            self.selected_point = self.hovered_point["filename"]
            self.point_double_clicked.emit(self.selected_point)

    def mouseReleaseEvent(self, event):
        self.last_mouse_pos = None

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        if delta > 0:
            self.zoom = min(5.0, self.zoom * 1.15)
        else:
            self.zoom = max(0.2, self.zoom / 1.15)
        self.update()


class EmbeddingMapDialog(QDialog):
    jump_to_image_signal = pyqtSignal(str)

    def __init__(self, parent=None, project=None):
        super().__init__(parent)
        self.project = project
        self.selected_image_to_jump = None
        self.target_jump_image = None
        self.worker = None

        self.setWindowTitle(tr("Интерактивная карта эмбеддингов датасета (t-SNE / PCA)"))
        self.setMinimumSize(980, 640)
        self.setStyleSheet(get_current_theme_style())

        self.setup_ui()
        self.run_embedding_analysis()

    def setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(12)

        # Левая часть: График и верхний тулбар
        plot_container = QWidget()
        plot_layout = QVBoxLayout(plot_container)
        plot_layout.setContentsMargins(0, 0, 0, 0)
        plot_layout.setSpacing(8)

        # Верхняя панель управления
        top_bar = QHBoxLayout()
        m_label = QLabel(tr("Метод проекции:"))
        self.method_combo = QComboBox()
        self.method_combo.addItem("PCA (Быстрый линейный)", "pca")
        self.method_combo.addItem("t-SNE (Кластеризация многообразий)", "tsne")
        self.method_combo.currentIndexChanged.connect(self.run_embedding_analysis)

        self.outliers_only_check = QCheckBox(tr("Только аномалии (Outliers)"))
        self.outliers_only_check.stateChanged.connect(self.on_outliers_filter_changed)

        self.reset_view_btn = QPushButton(tr("Центрировать"))
        self.reset_view_btn.clicked.connect(self.on_reset_view)

        top_bar.addWidget(m_label)
        top_bar.addWidget(self.method_combo)
        top_bar.addSpacing(16)
        top_bar.addWidget(self.outliers_only_check)
        top_bar.addStretch()
        top_bar.addWidget(self.reset_view_btn)
        plot_layout.addLayout(top_bar)

        # Прогресс-бар
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(4)
        plot_layout.addWidget(self.progress_bar)

        # 2D Холст
        self.canvas = EmbeddingCanvas(self, project=self.project)
        self.canvas.point_selected.connect(self.on_point_selected)
        self.canvas.point_double_clicked.connect(self.on_point_double_clicked)
        plot_layout.addWidget(self.canvas, 1)

        main_layout.addWidget(plot_container, 1)

        # Правая боковая панель: инфо о кадре и фильтры классов
        sidebar = QWidget()
        sidebar.setFixedWidth(280)
        sb_layout = QVBoxLayout(sidebar)
        sb_layout.setContentsMargins(0, 0, 0, 0)
        sb_layout.setSpacing(10)

        # 1. Информация о выбранном кадре
        info_group = QGroupBox(tr("Выбранное изображение"))
        ig_layout = QVBoxLayout(info_group)

        self.thumb_label = QLabel()
        self.thumb_label.setFixedSize(240, 150)
        self.thumb_label.setAlignment(Qt.AlignCenter)
        self.thumb_label.setStyleSheet("background-color: #18181b; border-radius: 6px;")
        ig_layout.addWidget(self.thumb_label)

        self.filename_label = QLabel(tr("Кликните на точку на карте"))
        self.filename_label.setWordWrap(True)
        self.filename_label.setStyleSheet("font-weight: bold; color: #f4f4f5;")
        ig_layout.addWidget(self.filename_label)

        self.meta_label = QLabel("")
        self.meta_label.setStyleSheet("color: #a1a1aa; font-size: 11px;")
        ig_layout.addWidget(self.meta_label)

        self.jump_btn = QPushButton(tr("Перейти к кадру в редакторе"))
        self.jump_btn.setFixedHeight(32)
        self.jump_btn.setEnabled(False)
        self.jump_btn.setStyleSheet("""
            QPushButton {
                background-color: #4f46e5;
                color: #ffffff;
                font-weight: bold;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #4338ca;
            }
        """)
        self.jump_btn.clicked.connect(self.jump_to_selected)
        ig_layout.addWidget(self.jump_btn)

        sb_layout.addWidget(info_group)

        # 2. Фильтр классов
        cls_group = QGroupBox(tr("Фильтр классов"))
        cg_layout = QVBoxLayout(cls_group)
        self.class_list = QListWidget()
        self.class_list.itemChanged.connect(self.on_class_item_changed)
        cg_layout.addWidget(self.class_list)
        sb_layout.addWidget(cls_group, 1)

        # Кнопка закрытия
        self.close_btn = QPushButton(tr("Закрыть"))
        self.close_btn.setFixedHeight(34)
        self.close_btn.clicked.connect(self.accept)
        sb_layout.addWidget(self.close_btn)

        main_layout.addWidget(sidebar)

    def run_embedding_analysis(self):
        if not self.project or not self.project.images_list:
            return

        method = self.method_combo.currentData()
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.method_combo.setEnabled(False)

        self.worker = EmbeddingWorker(project=self.project, method=method)
        self.worker.progress_signal.connect(self.progress_bar.setValue)
        self.worker.finished_signal.connect(self.on_analysis_finished)
        self.worker.start()

    def on_analysis_finished(self, results):
        self.method_combo.setEnabled(True)
        self.progress_bar.setVisible(False)

        points = results.get("points", [])
        classes = results.get("classes", [])

        self.canvas.set_data(points, classes)

        # Заполняем список классов
        self.class_list.clear()
        for cls_name in classes:
            item = QListWidgetItem(cls_name)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked)
            self.class_list.addItem(item)

    def on_point_selected(self, filename):
        self.selected_image_to_jump = filename
        self.filename_label.setText(filename)
        self.jump_btn.setEnabled(True)

        if not self.project:
            return

        full_path = os.path.join(self.project.images_dir, filename)
        if os.path.exists(full_path):
            pix = QPixmap(full_path)
            scaled = pix.scaled(self.thumb_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.thumb_label.setPixmap(scaled)

        # Метаданные
        boxes = self.project.get_annotations(filename, mode="main")
        pt_info = next((p for p in self.canvas.points if p["filename"] == filename), None)
        outlier_txt = f"\n⚠ {tr('Выброс / Аномалия')}" if (pt_info and pt_info["is_outlier"]) else ""
        self.meta_label.setText(f"{tr('Аннотаций на кадре')}: {len(boxes)}{outlier_txt}")

    def on_class_item_changed(self):
        active_classes = set()
        for r in range(self.class_list.count()):
            it = self.class_list.item(r)
            if it.checkState() == Qt.Checked:
                active_classes.add(it.text())
        self.canvas.visible_classes = active_classes
        self.canvas.update()

    def on_outliers_filter_changed(self):
        self.canvas.only_outliers = self.outliers_only_check.isChecked()
        self.canvas.update()

    def on_reset_view(self):
        self.canvas.reset_view()
        self.canvas.update()

    def on_point_double_clicked(self, filename):
        self.selected_image_to_jump = filename
        self.target_jump_image = filename
        self.accept()

    def jump_to_selected(self):
        if self.selected_image_to_jump:
            self.target_jump_image = self.selected_image_to_jump
            self.accept()

    def closeEvent(self, event):
        self._stop_worker()
        super().closeEvent(event)

    def reject(self):
        self._stop_worker()
        super().reject()

    def accept(self):
        self._stop_worker()
        super().accept()

    def _stop_worker(self):
        if self.worker is not None:
            try:
                self.worker.progress_signal.disconnect()
                self.worker.finished_signal.disconnect()
            except Exception:
                pass
            if self.worker.isRunning():
                self.worker.quit()
                self.worker.wait(150)
            self.worker = None
