# ui/track_interpolation_dialog.py
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QComboBox, QMessageBox, QGroupBox)
from PyQt5.QtCore import Qt
from ui.theme import get_current_theme_style
from core.track_interpolator import TrackInterpolator
from core.i18n import tr


class TrackInterpolationDialog(QDialog):
    def __init__(self, parent=None, project=None, current_image=None):
        super().__init__(parent)
        self.project = project
        self.current_image = current_image
        self.interpolated_count = 0

        self.setWindowTitle(tr("Интерполяция треков между ключевыми кадрами"))
        self.setMinimumSize(560, 400)
        self.setStyleSheet(get_current_theme_style())

        self.setup_ui()
        self.update_preview_info()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # 1. Выбор ключевых кадров
        f_group = QGroupBox(tr("Выбор ключевых кадров"))
        f_layout = QVBoxLayout(f_group)

        # Начальный кадр
        s_layout = QHBoxLayout()
        s_label = QLabel(tr("Начальный ключевой кадр (Start):"))
        s_label.setFixedWidth(200)
        self.start_combo = QComboBox()
        s_layout.addWidget(s_label)
        s_layout.addWidget(self.start_combo)
        f_layout.addLayout(s_layout)

        # Конечный кадр
        e_layout = QHBoxLayout()
        e_label = QLabel(tr("Конечный ключевой кадр (End):"))
        e_label.setFixedWidth(200)
        self.end_combo = QComboBox()
        e_layout.addWidget(e_label)
        e_layout.addWidget(self.end_combo)
        f_layout.addLayout(e_layout)

        # Режим аннотаций
        m_layout = QHBoxLayout()
        m_label = QLabel(tr("Целевой режим аннотаций:"))
        m_label.setFixedWidth(200)
        self.mode_combo = QComboBox()
        self.mode_combo.addItem(tr("Основной (Ручной)"), "main")
        self.mode_combo.addItem(tr("Нейросеть (Авто)"), "auto")
        m_layout.addWidget(m_label)
        m_layout.addWidget(self.mode_combo)
        f_layout.addLayout(m_layout)

        layout.addWidget(f_group)

        # Заполняем списки картинок
        if self.project and self.project.images_list:
            for img in self.project.images_list:
                self.start_combo.addItem(img)
                self.end_combo.addItem(img)

            # Выставляем по умолчанию: предыдущий размеченный и текущий
            if self.current_image in self.project.images_list:
                cur_idx = self.project.images_list.index(self.current_image)
                self.end_combo.setCurrentIndex(cur_idx)
                start_idx = max(0, cur_idx - 5)
                self.start_combo.setCurrentIndex(start_idx)

        self.start_combo.currentIndexChanged.connect(self.update_preview_info)
        self.end_combo.currentIndexChanged.connect(self.update_preview_info)
        self.mode_combo.currentIndexChanged.connect(self.update_preview_info)

        # 2. Сводная информация
        self.info_group = QGroupBox(tr("Сводка последовательности"))
        info_layout = QVBoxLayout(self.info_group)
        self.summary_label = QLabel()
        self.summary_label.setStyleSheet("color: #e4e4e7; font-size: 11px; line-height: 1.4;")
        info_layout.addWidget(self.summary_label)
        layout.addWidget(self.info_group)

        # 3. Кнопки
        btn_layout = QHBoxLayout()
        self.run_btn = QPushButton(tr("Интерполировать траектории"))
        self.run_btn.setFixedHeight(34)
        self.run_btn.setStyleSheet("""
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
        self.run_btn.clicked.connect(self.run_interpolation)

        self.cancel_btn = QPushButton(tr("Отмена"))
        self.cancel_btn.setFixedHeight(34)
        self.cancel_btn.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(self.run_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

    def update_preview_info(self):
        if not self.project or not self.project.images_list:
            self.summary_label.setText(tr("В проекте нет изображений."))
            self.run_btn.setEnabled(False)
            return

        start_img = self.start_combo.currentText()
        end_img = self.end_combo.currentText()
        mode = self.mode_combo.currentData()

        if not start_img or not end_img or start_img == end_img:
            self.summary_label.setText(tr("Выберите два РАЗНЫХ кадра для интерполяции."))
            self.run_btn.setEnabled(False)
            return

        idx_s = self.project.images_list.index(start_img)
        idx_e = self.project.images_list.index(end_img)
        if idx_s > idx_e:
            idx_s, idx_e = idx_e, idx_s
            start_img, end_img = end_img, start_img

        num_intermediate = idx_e - idx_s - 1
        boxes_s = self.project.get_annotations(start_img, mode=mode)
        boxes_e = self.project.get_annotations(end_img, mode=mode)

        if num_intermediate <= 0:
            self.summary_label.setText(tr("Кадры идут подряд, между ними нет промежуточных кадров."))
            self.run_btn.setEnabled(False)
            return

        self.summary_label.setText(
            f"• {tr('Промежуточных кадров для авторазметки')}: <b>{num_intermediate}</b> ({self.project.images_list[idx_s+1]} ... {self.project.images_list[idx_e-1]})<br>"
            f"• {tr('Объектов на начальном кадре')}: <b>{len(boxes_s)}</b><br>"
            f"• {tr('Объектов на конечном кадре')}: <b>{len(boxes_e)}</b>"
        )
        self.run_btn.setEnabled(True)

    def run_interpolation(self):
        start_img = self.start_combo.currentText()
        end_img = self.end_combo.currentText()
        mode = self.mode_combo.currentData()

        try:
            count = TrackInterpolator.interpolate_project_sequence(
                project=self.project,
                start_image=start_img,
                end_image=end_img,
                mode=mode
            )
            self.interpolated_count = count
            QMessageBox.information(
                self,
                tr("Успешно"),
                f"{tr('Успешно интерполированы траектории на')} {count} {tr('кадрах')}!"
            )
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, tr("Ошибка"), str(e))
