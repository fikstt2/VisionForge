# ui/inference_generator_dialog.py
import os
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QComboBox, QCheckBox, QLineEdit, 
                             QFileDialog, QMessageBox, QGroupBox, QTextEdit, 
                             QDoubleSpinBox, QApplication)
from PyQt5.QtGui import QFont
from ui.theme import get_current_theme_style
from core.i18n import tr


def generate_python_inference_code(model_path="best.pt", source_type="webcam", 
                                   source_path="0", conf=0.5, iou=0.45, 
                                   show_fps=True, save_output=False, 
                                   output_path="output.mp4"):
    """Генерация независимого чистого Python-скрипта инференса."""
    
    code = f'''#!/usr/bin/env python3
"""
Автоматически сгенерированный скрипт инференса VisionForge
Модель: {os.path.basename(model_path)}
Источник: {source_type}
"""

import cv2
import time
import argparse
from ultralytics import YOLO

def run_inference(
    model_path="{model_path}",
    source="{source_path}",
    conf_threshold={conf},
    iou_threshold={iou},
    show_fps={show_fps},
    save_output={save_output},
    output_path="{output_path}"
):
    print(f"🚀 Загрузка модели: {{model_path}}")
    model = YOLO(model_path)
    
    # Определение типа источника (веб-камера, видеофайл или поток)
    if source.isdigit():
        cap = cv2.VideoCapture(int(source))
    else:
        cap = cv2.VideoCapture(source)

    if not cap.isOpened():
        print(f"❌ Ошибка: не удалось открыть источник {{source}}")
        return

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0

    writer = None
    if save_output:
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        print(f"📹 Запись результата в: {{output_path}}")

    prev_time = time.time()
    print("✨ Инференс запущен. Нажмите 'Q' для выхода.")

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        # Запуск детекции / сегментации
        results = model.predict(
            source=frame,
            conf=conf_threshold,
            iou=iou_threshold,
            verbose=False
        )

        # Отрисовка результатов
        annotated_frame = results[0].plot()

        if show_fps:
            curr_time = time.time()
            fps_val = 1.0 / (curr_time - prev_time) if (curr_time - prev_time) > 0 else 0
            prev_time = curr_time
            cv2.putText(
                annotated_frame,
                f"FPS: {{fps_val:.1f}}",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.0,
                (0, 255, 0),
                2,
                cv2.LINE_AA
            )

        cv2.imshow("VisionForge Inference", annotated_frame)
        if writer:
            writer.write(annotated_frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    if writer:
        writer.release()
    cv2.destroyAllWindows()
    print("✅ Инференс завершен.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VisionForge Standalone Inference")
    parser.add_argument("--model", type=str, default="{model_path}", help="Путь к модели (.pt / .onnx / .engine)")
    parser.add_argument("--source", type=str, default="{source_path}", help="Источник (0 для камеры, путь к видео или RTSP)")
    parser.add_argument("--conf", type=float, default={conf}, help="Порог уверенности (Confidence)")
    parser.add_argument("--iou", type=float, default={iou}, help="Порог NMS IoU")
    parser.add_argument("--save", action="store_true", default={save_output}, help="Сохранять выходное видео")
    parser.add_argument("--out", type=str, default="{output_path}", help="Путь к выходному файлу")
    args = parser.parse_args()

    run_inference(
        model_path=args.model,
        source=args.source,
        conf_threshold=args.conf,
        iou_threshold=args.iou,
        show_fps={show_fps},
        save_output=args.save,
        output_path=args.out
    )
'''
    return code


class InferenceGeneratorDialog(QDialog):
    def __init__(self, parent=None, default_model_path=None):
        super().__init__(parent)
        self.default_model_path = default_model_path or "best.pt"

        self.setWindowTitle(tr("Генератор автономного Python-скрипта инференса"))
        self.setMinimumSize(780, 620)
        self.setStyleSheet(get_current_theme_style())

        self.setup_ui()
        self.update_preview()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # 1. Параметры скрипта
        cfg_group = QGroupBox(tr("Параметры инференса"))
        cfg_layout = QVBoxLayout(cfg_group)

        # Путь к модели
        m_layout = QHBoxLayout()
        m_label = QLabel(tr("Файл модели:"))
        m_label.setFixedWidth(130)
        self.model_path_edit = QLineEdit(self.default_model_path)
        self.browse_model_btn = QPushButton(tr("Обзор..."))
        self.browse_model_btn.clicked.connect(self.browse_model)
        self.model_path_edit.textChanged.connect(self.update_preview)
        m_layout.addWidget(m_label)
        m_layout.addWidget(self.model_path_edit)
        m_layout.addWidget(self.browse_model_btn)
        cfg_layout.addLayout(m_layout)

        # Источник
        s_layout = QHBoxLayout()
        s_label = QLabel(tr("Источник видео:"))
        s_label.setFixedWidth(130)
        self.source_combo = QComboBox()
        self.source_combo.addItems([
            tr("Веб-камера (0)"),
            tr("Видеофайл (.mp4, .avi)"),
            tr("RTSP Поток"),
            tr("Вторая камера (1)")
        ])
        self.source_combo.currentIndexChanged.connect(self.on_source_changed)
        self.source_edit = QLineEdit("0")
        self.source_edit.textChanged.connect(self.update_preview)
        self.browse_source_btn = QPushButton(tr("Файл..."))
        self.browse_source_btn.setVisible(False)
        self.browse_source_btn.clicked.connect(self.browse_source_file)

        s_layout.addWidget(s_label)
        s_layout.addWidget(self.source_combo)
        s_layout.addWidget(self.source_edit)
        s_layout.addWidget(self.browse_source_btn)
        cfg_layout.addLayout(s_layout)

        # Пороги и опции
        p_layout = QHBoxLayout()
        conf_label = QLabel(tr("Порог Confidence:"))
        self.conf_spin = QDoubleSpinBox()
        self.conf_spin.setRange(0.01, 1.0)
        self.conf_spin.setSingleStep(0.05)
        self.conf_spin.setValue(0.50)
        self.conf_spin.valueChanged.connect(self.update_preview)

        iou_label = QLabel(tr("Порог IoU:"))
        self.iou_spin = QDoubleSpinBox()
        self.iou_spin.setRange(0.01, 1.0)
        self.iou_spin.setSingleStep(0.05)
        self.iou_spin.setValue(0.45)
        self.iou_spin.valueChanged.connect(self.update_preview)

        self.fps_check = QCheckBox(tr("Отображать FPS"))
        self.fps_check.setChecked(True)
        self.fps_check.stateChanged.connect(self.update_preview)

        self.save_check = QCheckBox(tr("Сохранять результат в видео"))
        self.save_check.setChecked(False)
        self.save_check.stateChanged.connect(self.update_preview)

        p_layout.addWidget(conf_label)
        p_layout.addWidget(self.conf_spin)
        p_layout.addWidget(iou_label)
        p_layout.addWidget(self.iou_spin)
        p_layout.addWidget(self.fps_check)
        p_layout.addWidget(self.save_check)
        p_layout.addStretch()
        cfg_layout.addLayout(p_layout)

        layout.addWidget(cfg_group)

        # 2. Предпросмотр сгенерированного кода
        code_group = QGroupBox(tr("Сгенерированный код Python"))
        code_layout = QVBoxLayout(code_group)
        self.code_view = QTextEdit()
        self.code_view.setFont(QFont("Consolas", 10))
        self.code_view.setStyleSheet("""
            QTextEdit {
                background-color: #121216;
                color: #e4e4e7;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 6px;
                padding: 6px;
            }
        """)
        code_layout.addWidget(self.code_view)
        layout.addWidget(code_group)

        # 3. Кнопки действий
        btn_layout = QHBoxLayout()
        self.copy_btn = QPushButton(tr("Копировать в буфер"))
        self.copy_btn.setFixedHeight(34)
        self.copy_btn.clicked.connect(self.copy_code)

        self.save_script_btn = QPushButton(tr("Сохранить скрипт (.py)..."))
        self.save_script_btn.setFixedHeight(34)
        self.save_script_btn.setStyleSheet("""
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
        self.save_script_btn.clicked.connect(self.save_script)

        self.close_btn = QPushButton(tr("Закрыть"))
        self.close_btn.setFixedHeight(34)
        self.close_btn.clicked.connect(self.reject)

        btn_layout.addWidget(self.copy_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.save_script_btn)
        btn_layout.addWidget(self.close_btn)
        layout.addLayout(btn_layout)

    def on_source_changed(self, index):
        if index == 0:
            self.source_edit.setText("0")
            self.browse_source_btn.setVisible(False)
        elif index == 1:
            self.source_edit.setText("video.mp4")
            self.browse_source_btn.setVisible(True)
        elif index == 2:
            self.source_edit.setText("rtsp://admin:password@192.168.1.100:554/stream1")
            self.browse_source_btn.setVisible(False)
        elif index == 3:
            self.source_edit.setText("1")
            self.browse_source_btn.setVisible(False)
        self.update_preview()

    def browse_model(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            tr("Выберите модель"),
            os.getcwd(),
            "Models (*.pt *.onnx *.engine);;All Files (*.*)"
        )
        if path:
            self.model_path_edit.setText(path)

    def browse_source_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            tr("Выберите видеофайл"),
            os.getcwd(),
            "Videos (*.mp4 *.avi *.mkv *.mov);;All Files (*.*)"
        )
        if path:
            self.source_edit.setText(path)

    def update_preview(self):
        src_type_str = self.source_combo.currentText()
        code = generate_python_inference_code(
            model_path=self.model_path_edit.text().strip() or "best.pt",
            source_type=src_type_str,
            source_path=self.source_edit.text().strip() or "0",
            conf=self.conf_spin.value(),
            iou=self.iou_spin.value(),
            show_fps=self.fps_check.isChecked(),
            save_output=self.save_check.isChecked(),
            output_path="output.mp4"
        )
        self.code_view.setPlainText(code)

    def copy_code(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.code_view.toPlainText())
        QMessageBox.information(self, tr("Успех"), tr("Код скопирован в буфер обмена!"))

    def save_script(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            tr("Сохранить Python-скрипт инференса"),
            os.path.join(os.getcwd(), "inference.py"),
            "Python Files (*.py);;All Files (*.*)"
        )
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(self.code_view.toPlainText())
                QMessageBox.information(
                    self,
                    tr("Сохранено"),
                    f"{tr('Скрипт успешно сохранен')}:\n{path}"
                )
            except Exception as e:
                QMessageBox.critical(self, tr("Ошибка"), str(e))
