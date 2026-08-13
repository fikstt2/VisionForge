# ui/augmentation_sandbox_dialog.py
import os
import cv2
import numpy as np
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QComboBox, QCheckBox, QSlider, 
                             QGroupBox, QSplitter, QMessageBox, QScrollArea, QWidget)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage, QPixmap, QPainter, QPen, QColor, QPolygon
from PyQt5.QtCore import QPoint
from ui.theme import get_current_theme_style
from core.augmentation_engine import AugmentationEngine
from core.i18n import tr


class AugmentationSandboxDialog(QDialog):
    def __init__(self, parent=None, project=None, current_image_name=None):
        super().__init__(parent)
        self.project = project
        self.current_image_name = current_image_name
        self.img_orig = None
        self.boxes_orig = []
        self.aug_img = None
        self.aug_boxes = []

        self.setWindowTitle(tr("Интерактивная песочница аугментаций"))
        self.setMinimumSize(960, 680)
        self.setStyleSheet(get_current_theme_style())

        self.setup_ui()
        self.load_image_data()
        self.apply_live_preview()

    def setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(12)

        # Левая панель: ползунки управления
        controls_scroll = QScrollArea()
        controls_scroll.setWidgetResizable(True)
        controls_scroll.setFixedWidth(330)
        controls_widget = QWidget()
        ctrl_layout = QVBoxLayout(controls_widget)
        ctrl_layout.setSpacing(10)

        # Выбор изображения
        img_group = QGroupBox(tr("Текущее изображение"))
        img_layout = QVBoxLayout(img_group)
        self.img_combo = QComboBox()
        if self.project and self.project.images_list:
            for img_name in self.project.images_list:
                self.img_combo.addItem(img_name)
            if self.current_image_name in self.project.images_list:
                self.img_combo.setCurrentText(self.current_image_name)
        self.img_combo.currentIndexChanged.connect(self.on_image_combo_changed)
        img_layout.addWidget(self.img_combo)
        ctrl_layout.addWidget(img_group)

        # 1. Геометрия
        geo_group = QGroupBox(tr("Геометрические трансформации"))
        geo_layout = QVBoxLayout(geo_group)

        self.flip_h_check = QCheckBox(tr("Отразить по горизонтали (Flip H)"))
        self.flip_h_check.stateChanged.connect(self.apply_live_preview)
        self.flip_v_check = QCheckBox(tr("Отразить по вертикали (Flip V)"))
        self.flip_v_check.stateChanged.connect(self.apply_live_preview)
        geo_layout.addWidget(self.flip_h_check)
        geo_layout.addWidget(self.flip_v_check)

        # Поворот
        self.rot_label = QLabel(f"{tr('Поворот')}: 0°")
        self.rot_slider = QSlider(Qt.Horizontal)
        self.rot_slider.setRange(-90, 90)
        self.rot_slider.setValue(0)
        self.rot_slider.valueChanged.connect(self.on_slider_changed)
        geo_layout.addWidget(self.rot_label)
        geo_layout.addWidget(self.rot_slider)

        # Масштаб
        self.scale_label = QLabel(f"{tr('Масштаб')}: 1.0x")
        self.scale_slider = QSlider(Qt.Horizontal)
        self.scale_slider.setRange(50, 150)
        self.scale_slider.setValue(100)
        self.scale_slider.valueChanged.connect(self.on_slider_changed)
        geo_layout.addWidget(self.scale_label)
        geo_layout.addWidget(self.scale_slider)

        # Сдвиг
        self.shift_label = QLabel(f"{tr('Сдвиг X')}: 0%")
        self.shift_slider = QSlider(Qt.Horizontal)
        self.shift_slider.setRange(-30, 30)
        self.shift_slider.setValue(0)
        self.shift_slider.valueChanged.connect(self.on_slider_changed)
        geo_layout.addWidget(self.shift_label)
        geo_layout.addWidget(self.shift_slider)

        ctrl_layout.addWidget(geo_group)

        # 2. Цвет и HSV
        col_group = QGroupBox(tr("Цветовые параметры (HSV)"))
        col_layout = QVBoxLayout(col_group)

        self.hue_label = QLabel(f"{tr('Оттенок (Hue)')}: 0.0")
        self.hue_slider = QSlider(Qt.Horizontal)
        self.hue_slider.setRange(-50, 50)
        self.hue_slider.setValue(0)
        self.hue_slider.valueChanged.connect(self.on_slider_changed)
        col_layout.addWidget(self.hue_label)
        col_layout.addWidget(self.hue_slider)

        self.sat_label = QLabel(f"{tr('Насыщенность (Sat)')}: 1.0x")
        self.sat_slider = QSlider(Qt.Horizontal)
        self.sat_slider.setRange(0, 200)
        self.sat_slider.setValue(100)
        self.sat_slider.valueChanged.connect(self.on_slider_changed)
        col_layout.addWidget(self.sat_label)
        col_layout.addWidget(self.sat_slider)

        self.val_label = QLabel(f"{tr('Яркость (Val)')}: 1.0x")
        self.val_slider = QSlider(Qt.Horizontal)
        self.val_slider.setRange(20, 200)
        self.val_slider.setValue(100)
        self.val_slider.valueChanged.connect(self.on_slider_changed)
        col_layout.addWidget(self.val_label)
        col_layout.addWidget(self.val_slider)

        ctrl_layout.addWidget(col_group)

        # 3. Шум, Размытие и Погода
        fx_group = QGroupBox(tr("Шум, Размытие и Эффекты"))
        fx_layout = QVBoxLayout(fx_group)

        self.blur_label = QLabel(f"{tr('Размытие (Blur)')}: 0")
        self.blur_slider = QSlider(Qt.Horizontal)
        self.blur_slider.setRange(0, 15)
        self.blur_slider.setValue(0)
        self.blur_slider.valueChanged.connect(self.on_slider_changed)
        fx_layout.addWidget(self.blur_label)
        fx_layout.addWidget(self.blur_slider)

        self.noise_label = QLabel(f"{tr('Шум (Noise)')}: 0")
        self.noise_slider = QSlider(Qt.Horizontal)
        self.noise_slider.setRange(0, 40)
        self.noise_slider.setValue(0)
        self.noise_slider.valueChanged.connect(self.on_slider_changed)
        fx_layout.addWidget(self.noise_label)
        fx_layout.addWidget(self.noise_slider)

        # Погода
        w_layout = QHBoxLayout()
        w_label = QLabel(tr("Эффект:"))
        self.weather_combo = QComboBox()
        self.weather_combo.addItem(tr("Нет"), "none")
        self.weather_combo.addItem(tr("Дождь"), "rain")
        self.weather_combo.addItem(tr("Туман"), "fog")
        self.weather_combo.currentIndexChanged.connect(self.apply_live_preview)
        w_layout.addWidget(w_label)
        w_layout.addWidget(self.weather_combo)
        fx_layout.addLayout(w_layout)

        # Cutout
        self.cutout_label = QLabel(f"{tr('Cutout (вырезы)')}: 0")
        self.cutout_slider = QSlider(Qt.Horizontal)
        self.cutout_slider.setRange(0, 4)
        self.cutout_slider.setValue(0)
        self.cutout_slider.valueChanged.connect(self.on_slider_changed)
        fx_layout.addWidget(self.cutout_label)
        fx_layout.addWidget(self.cutout_slider)

        ctrl_layout.addWidget(fx_group)

        # Кнопка сброса
        self.reset_btn = QPushButton(tr("Сбросить параметры"))
        self.reset_btn.clicked.connect(self.reset_controls)
        ctrl_layout.addWidget(self.reset_btn)

        controls_scroll.setWidget(controls_widget)
        main_layout.addWidget(controls_scroll)

        # Правая панель: область предпросмотра
        preview_container = QWidget()
        prev_layout = QVBoxLayout(preview_container)
        prev_layout.setContentsMargins(0, 0, 0, 0)

        # Вьюпорт предпросмотра
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setStyleSheet("background-color: #121216; border: 1px solid #27272a; border-radius: 8px;")
        prev_layout.addWidget(self.preview_label, 1)

        # Нижняя панель действий
        bottom_layout = QHBoxLayout()
        self.save_to_project_btn = QPushButton(tr("Сохранить копию в датасет"))
        self.save_to_project_btn.setFixedHeight(34)
        self.save_to_project_btn.setStyleSheet("""
            QPushButton {
                background-color: #4f46e5;
                color: #ffffff;
                font-weight: bold;
                border-radius: 6px;
                padding: 0 16px;
            }
            QPushButton:hover {
                background-color: #4338ca;
            }
        """)
        self.save_to_project_btn.clicked.connect(self.save_augmented_copy)

        self.close_btn = QPushButton(tr("Закрыть"))
        self.close_btn.setFixedHeight(34)
        self.close_btn.clicked.connect(self.accept)

        bottom_layout.addWidget(self.save_to_project_btn)
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.close_btn)
        prev_layout.addLayout(bottom_layout)

        main_layout.addWidget(preview_container, 1)

    def on_image_combo_changed(self):
        self.current_image_name = self.img_combo.currentText()
        self.load_image_data()
        self.apply_live_preview()

    def load_image_data(self):
        if not self.project or not self.current_image_name:
            return
        path = os.path.join(self.project.images_dir, self.current_image_name)
        if os.path.exists(path):
            bgr = cv2.imread(path)
            if bgr is not None:
                self.img_orig = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
                self.boxes_orig = self.project.get_annotations(self.current_image_name, mode="main")

    def on_slider_changed(self):
        self.rot_label.setText(f"{tr('Поворот')}: {self.rot_slider.value()}°")
        self.scale_label.setText(f"{tr('Масштаб')}: {self.scale_slider.value() / 100.0:.2f}x")
        self.shift_label.setText(f"{tr('Сдвиг X')}: {self.shift_slider.value()}%")
        self.hue_label.setText(f"{tr('Оттенок (Hue)')}: {self.hue_slider.value() / 100.0:.2f}")
        self.sat_label.setText(f"{tr('Насыщенность (Sat)')}: {self.sat_slider.value() / 100.0:.2f}x")
        self.val_label.setText(f"{tr('Яркость (Val)')}: {self.val_slider.value() / 100.0:.2f}x")
        self.blur_label.setText(f"{tr('Размытие (Blur)')}: {self.blur_slider.value()}")
        self.noise_label.setText(f"{tr('Шум (Noise)')}: {self.noise_slider.value()}")
        self.cutout_label.setText(f"{tr('Cutout (вырезы)')}: {self.cutout_slider.value()}")
        self.apply_live_preview()

    def reset_controls(self):
        self.flip_h_check.setChecked(False)
        self.flip_v_check.setChecked(False)
        self.rot_slider.setValue(0)
        self.scale_slider.setValue(100)
        self.shift_slider.setValue(0)
        self.hue_slider.setValue(0)
        self.sat_slider.setValue(100)
        self.val_slider.setValue(100)
        self.blur_slider.setValue(0)
        self.noise_slider.setValue(0)
        self.weather_combo.setCurrentIndex(0)
        self.cutout_slider.setValue(0)
        self.apply_live_preview()

    def get_current_params(self):
        return {
            "flip_h": self.flip_h_check.isChecked(),
            "flip_v": self.flip_v_check.isChecked(),
            "rotation": float(self.rot_slider.value()),
            "scale": float(self.scale_slider.value()) / 100.0,
            "shift_x": float(self.shift_slider.value()) / 100.0,
            "shift_y": 0.0,
            "hsv_h": float(self.hue_slider.value()) / 100.0,
            "hsv_s": float(self.sat_slider.value()) / 100.0,
            "hsv_v": float(self.val_slider.value()) / 100.0,
            "blur": int(self.blur_slider.value()),
            "noise": float(self.noise_slider.value()),
            "weather": self.weather_combo.currentData(),
            "cutout_count": int(self.cutout_slider.value())
        }

    def apply_live_preview(self):
        if self.img_orig is None:
            return

        params = self.get_current_params()
        self.aug_img, self.aug_boxes = AugmentationEngine.apply_transformations(
            self.img_orig, self.boxes_orig, params
        )

        h, w, ch = self.aug_img.shape
        bytes_per_line = ch * w
        qimg = QImage(self.aug_img.data, w, h, bytes_per_line, QImage.Format_RGB888).copy()
        pixmap = QPixmap.fromImage(qimg)

        # Отрисовываем боксы и полигоны поверх
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        for b in self.aug_boxes:
            cls_name = b.get("class", "unknown")
            color_hex = self.project.class_colors.get(cls_name, "#4f46e5") if self.project else "#4f46e5"
            color = QColor(color_hex)

            if "polygon" in b and b["polygon"]:
                pts = [QPoint(int(p[0]), int(p[1])) for p in b["polygon"]]
                if len(pts) >= 3:
                    poly = QPolygon(pts)
                    painter.setPen(QPen(color, 2))
                    fill_c = QColor(color)
                    fill_c.setAlpha(40)
                    painter.setBrush(fill_c)
                    painter.drawPolygon(poly)
                    painter.setBrush(Qt.NoBrush)
                    painter.drawText(pts[0].x(), max(15, pts[0].y() - 5), cls_name)
            elif "bbox" in b and b["bbox"]:
                x1, y1, x2, y2 = b["bbox"]
                painter.setPen(QPen(color, 2))
                painter.setBrush(Qt.NoBrush)
                painter.drawRect(x1, y1, x2 - x1, y2 - y1)
                painter.drawText(x1, max(15, y1 - 5), cls_name)

        painter.end()

        # Масштабируем под вьюпорт
        lbl_size = self.preview_label.size()
        scaled = pixmap.scaled(lbl_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.preview_label.setPixmap(scaled)

    def save_augmented_copy(self):
        if not self.project or self.aug_img is None or not self.current_image_name:
            return

        base, ext = os.path.splitext(self.current_image_name)
        new_filename = f"{base}_aug_{np.random.randint(1000, 9999)}{ext}"
        new_path = os.path.join(self.project.images_dir, new_filename)

        # Сохраняем картинку
        bgr = cv2.cvtColor(self.aug_img, cv2.COLOR_RGB2BGR)
        cv2.imwrite(new_path, bgr)

        # Добавляем в проект
        self.project.images_list.append(new_filename)
        self.project.images_list.sort()
        self.project.set_annotations(new_filename, self.aug_boxes, mode="main")
        self.project.save()

        QMessageBox.information(
            self,
            tr("Сохранено"),
            f"{tr('Аугментированная копия успешно добавлена в проект')}:\n{new_filename}"
        )
