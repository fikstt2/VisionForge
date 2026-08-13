# ui/video_extractor_dialog.py
import os
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QComboBox, QLineEdit, QFileDialog, 
                             QMessageBox, QGroupBox, QSpinBox, QDoubleSpinBox, 
                             QProgressBar, QRadioButton, QButtonGroup)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from ui.theme import get_current_theme_style
from core.video_extractor import VideoExtractor
from core.i18n import tr


class VideoExtractorWorker(QThread):
    progress_signal = pyqtSignal(int, int, int)  # pct, saved_count, frame_idx
    finished_signal = pyqtSignal(bool, str, list)

    def __init__(self, video_path, output_dir, prefix, step_type, interval, target_fps, scene_threshold, max_frames):
        super().__init__()
        self.video_path = video_path
        self.output_dir = output_dir
        self.prefix = prefix
        self.step_type = step_type
        self.interval = interval
        self.target_fps = target_fps
        self.scene_threshold = scene_threshold
        self.max_frames = max_frames
        self.cancelled = False

    def run(self):
        try:
            def cancel_check():
                return self.cancelled

            def on_progress(pct, saved, current_frame):
                self.progress_signal.emit(pct, saved, current_frame)

            extracted = VideoExtractor.extract_frames(
                video_path=self.video_path,
                output_dir=self.output_dir,
                prefix=self.prefix,
                step_type=self.step_type,
                interval=self.interval,
                target_fps=self.target_fps,
                scene_threshold=self.scene_threshold,
                max_frames=self.max_frames,
                progress_callback=on_progress,
                cancel_check=cancel_check
            )

            if self.cancelled:
                self.finished_signal.emit(False, tr("Извлечение отменено пользователем"), extracted)
            else:
                self.finished_signal.emit(True, f"{tr('Успешно извлечено кадров')}: {len(extracted)}", extracted)
        except Exception as e:
            self.finished_signal.emit(False, str(e), [])

    def cancel(self):
        self.cancelled = True


class VideoExtractorDialog(QDialog):
    def __init__(self, parent=None, project=None):
        super().__init__(parent)
        self.project = project
        self.worker = None
        self.extracted_files = []

        self.setWindowTitle(tr("Импорт видео и покадровая нарезка"))
        self.setMinimumSize(640, 520)
        self.setStyleSheet(get_current_theme_style())

        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # 1. Выбор видеофайла
        v_group = QGroupBox(tr("Видеофайл"))
        v_layout = QVBoxLayout(v_group)

        file_layout = QHBoxLayout()
        self.video_path_edit = QLineEdit()
        self.video_path_edit.setPlaceholderText(tr("Выберите видеофайл (.mp4, .avi, .mkv, .mov)..."))
        self.browse_video_btn = QPushButton(tr("Обзор..."))
        self.browse_video_btn.clicked.connect(self.browse_video)
        file_layout.addWidget(self.video_path_edit)
        file_layout.addWidget(self.browse_video_btn)
        v_layout.addLayout(file_layout)

        # Информация о видео
        self.info_label = QLabel(tr("Видео не выбрано"))
        self.info_label.setStyleSheet("color: #a1a1aa; font-size: 11px; margin-top: 4px;")
        v_layout.addWidget(self.info_label)
        layout.addWidget(v_group)

        # 2. Режим нарезки
        mode_group = QGroupBox(tr("Параметры извлечения кадров"))
        mode_layout = QVBoxLayout(mode_group)

        self.btn_group = QButtonGroup(self)

        # Режим 1: По интервалу
        self.radio_interval = QRadioButton(tr("Каждый N-й кадр (по интервалу):"))
        self.radio_interval.setChecked(True)
        self.spin_interval = QSpinBox()
        self.spin_interval.setRange(1, 1000)
        self.spin_interval.setValue(5)
        self.btn_group.addButton(self.radio_interval)

        r1_layout = QHBoxLayout()
        r1_layout.addWidget(self.radio_interval)
        r1_layout.addWidget(self.spin_interval)
        r1_layout.addStretch()
        mode_layout.addLayout(r1_layout)

        # Режим 2: По FPS
        self.radio_fps = QRadioButton(tr("По заданной частоте (FPS):"))
        self.spin_fps = QDoubleSpinBox()
        self.spin_fps.setRange(0.1, 60.0)
        self.spin_fps.setSingleStep(0.5)
        self.spin_fps.setValue(2.0)
        self.btn_group.addButton(self.radio_fps)

        r2_layout = QHBoxLayout()
        r2_layout.addWidget(self.radio_fps)
        r2_layout.addWidget(self.spin_fps)
        r2_layout.addStretch()
        mode_layout.addLayout(r2_layout)

        # Режим 3: Детекция смены сцен
        self.radio_scene = QRadioButton(tr("Детекция смены сцен (Keyframes):"))
        self.spin_scene = QDoubleSpinBox()
        self.spin_scene.setRange(5.0, 100.0)
        self.spin_scene.setValue(25.0)
        self.btn_group.addButton(self.radio_scene)

        r3_layout = QHBoxLayout()
        r3_layout.addWidget(self.radio_scene)
        r3_layout.addWidget(self.spin_scene)
        r3_layout.addStretch()
        mode_layout.addLayout(r3_layout)

        # Ограничение максимума кадров
        limit_layout = QHBoxLayout()
        limit_label = QLabel(tr("Максимум кадров:"))
        self.spin_max_frames = QSpinBox()
        self.spin_max_frames.setRange(10, 50000)
        self.spin_max_frames.setValue(1000)
        limit_layout.addWidget(limit_label)
        limit_layout.addWidget(self.spin_max_frames)
        limit_layout.addStretch()
        mode_layout.addLayout(limit_layout)

        layout.addWidget(mode_group)

        # 3. Папка назначения
        dst_group = QGroupBox(tr("Папка сохранения"))
        dst_layout = QHBoxLayout(dst_group)
        default_dir = self.project.images_dir if self.project else os.getcwd()
        self.dst_path_edit = QLineEdit(default_dir)
        self.browse_dst_btn = QPushButton(tr("Обзор..."))
        self.browse_dst_btn.clicked.connect(self.browse_dst)
        dst_layout.addWidget(self.dst_path_edit)
        dst_layout.addWidget(self.browse_dst_btn)
        layout.addWidget(dst_group)

        # 4. Прогресс
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #818cf8; font-weight: 600; font-size: 11px;")
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.status_label)

        # 5. Кнопки
        btn_layout = QHBoxLayout()
        self.start_btn = QPushButton(tr("Начать нарезку"))
        self.start_btn.setFixedHeight(34)
        self.start_btn.setStyleSheet("""
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
        self.start_btn.clicked.connect(self.start_extraction)

        self.cancel_btn = QPushButton(tr("Отмена"))
        self.cancel_btn.setFixedHeight(34)
        self.cancel_btn.clicked.connect(self.on_cancel)

        btn_layout.addStretch()
        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

    def browse_video(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            tr("Выберите видеофайл"),
            os.getcwd(),
            "Video Files (*.mp4 *.avi *.mkv *.mov *.webm *.wmv);;All Files (*.*)"
        )
        if path:
            self.video_path_edit.setText(path)
            try:
                info = VideoExtractor.get_video_info(path)
                self.info_label.setText(
                    f"{tr('Длительность')}: {info['duration_sec']} с | "
                    f"FPS: {info['fps']} | "
                    f"{tr('Разрешение')}: {info['width']}x{info['height']} | "
                    f"{tr('Всего кадров')}: {info['total_frames']}"
                )
            except Exception as e:
                self.info_label.setText(f"{tr('Ошибка чтения информации')}: {e}")

    def browse_dst(self):
        folder = QFileDialog.getExistingDirectory(self, tr("Выберите папку для сохранения кадров"))
        if folder:
            self.dst_path_edit.setText(folder)

    def start_extraction(self):
        video_path = self.video_path_edit.text().strip()
        if not video_path or not os.path.exists(video_path):
            QMessageBox.warning(self, tr("Ошибка"), tr("Укажите существующий видеофайл"))
            return

        out_dir = self.dst_path_edit.text().strip()
        if not out_dir:
            QMessageBox.warning(self, tr("Ошибка"), tr("Укажите папку сохранения"))
            return

        if self.radio_interval.isChecked():
            step_type = "interval"
        elif self.radio_fps.isChecked():
            step_type = "fps"
        else:
            step_type = "scene"

        self.start_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText(tr("Обработка видео..."))

        self.worker = VideoExtractorWorker(
            video_path=video_path,
            output_dir=out_dir,
            prefix=None,
            step_type=step_type,
            interval=self.spin_interval.value(),
            target_fps=self.spin_fps.value(),
            scene_threshold=self.spin_scene.value(),
            max_frames=self.spin_max_frames.value()
        )
        self.worker.progress_signal.connect(self.on_progress)
        self.worker.finished_signal.connect(self.on_finished)
        self.worker.start()

    def on_progress(self, pct, saved, current_frame):
        self.progress_bar.setValue(pct)
        self.status_label.setText(f"{tr('Извлечено кадров')}: {saved} ({tr('Обработано кадров видео')}: {current_frame})")

    def on_finished(self, success, msg, files):
        self.start_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        if success:
            self.extracted_files = files
            QMessageBox.information(
                self,
                tr("Готово"),
                f"{msg}\n\n{tr('Кадры сохранены в')}:\n{self.dst_path_edit.text()}"
            )
            self.accept()
        else:
            QMessageBox.warning(self, tr("Внимание"), msg)

    def on_cancel(self):
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait()
        self.reject()
