# detection/overlay.py
import cv2
import numpy as np
import time
import json
import os
import traceback
from collections import deque
from threading import Lock
import mss

from PyQt5.QtWidgets import (QApplication, QMainWindow, QOpenGLWidget,
                             QDialog, QVBoxLayout, QLabel,
                             QSlider, QSpinBox, QCheckBox, QPushButton)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QPainter, QPen, QColor, QFont
from OpenGL import GL as gl
import ctypes

import config
from core.utils import draw_text_cv2
from core.i18n import tr

# Глобальные настройки (будут изменяться через клавиши и диалог)
CAPTURE_SCALE = 0.8
DET_IMG_SIZE = 1024
FRAME_SKIP = 2
SHOW_TRACKS = True

class CaptureThread(QThread):
    def __init__(self, scale=1.0):
        super().__init__()
        self.scale = scale
        self.running = True
        self.frame_queue = deque(maxlen=2)
        self.lock = Lock()

    def run(self):
        try:
            with mss.mss() as sct:
                monitor = sct.monitors[1]
                while self.running:
                    img = sct.grab(monitor)
                    frame = np.array(img)
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                    if self.scale != 1.0:
                        h, w = frame.shape[:2]
                        new_w = int(w * self.scale)
                        new_h = int(h * self.scale)
                        frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_NEAREST)
                    with self.lock:
                        self.frame_queue.append(frame)
                    self.msleep(1)
        except Exception as e:
            print(f"CaptureThread error: {e}")
        finally:
            print("CaptureThread finished")

    def stop(self):
        self.running = False

    def get_latest_frame(self):
        with self.lock:
            return self.frame_queue[-1] if self.frame_queue else None

class DetectorThread(QThread):
    results_ready = pyqtSignal(list, int, int)  # boxes, orig_w, orig_h
    fps_updated = pyqtSignal(float, float, int, int)

    def __init__(self, detector, classifier, capture_thread):
        super().__init__()
        self.detector = detector
        self.classifier = classifier
        self.capture = capture_thread
        self.running = True
        self.frame_skip = FRAME_SKIP
        self.det_conf = 0.4
        self.cls_conf = config.load_config().get("cls_conf", 0.5)
        self.imgsz = DET_IMG_SIZE
        self.frame_counter = 0
        self.classifier_enabled = False
        self.last_boxes = []

        self.fps_counter = 0
        self.fps_last_time = time.time()
        self.fps = 0.0

    def stop(self):
        self.running = False

    def run(self):
        try:
            while self.running:
                frame = self.capture.get_latest_frame()
                if frame is None:
                    self.msleep(1)
                    continue

                self.frame_counter += 1
                if self.frame_counter % self.frame_skip != 0:
                    self.msleep(1)
                    continue

                results = self.detector.track(
                    frame,
                    conf=self.det_conf,
                    iou=0.5,
                    imgsz=self.imgsz,
                    persist=True,
                    verbose=False
                )[0]

                boxes_list = []
                if results.boxes is not None and len(results.boxes) > 0:
                    for box in results.boxes:
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        conf = float(box.conf[0])
                        cls_id = int(box.cls[0])
                        track_id = int(box.id[0]) if box.id is not None else None

                        # Убрана проверка на show_destroyed
                        label = f"{tr('объект')} {conf:.2f}"
                        if SHOW_TRACKS and track_id is not None:
                            label = f"{label} #{track_id}"

                        color = (255, 0, 0) if cls_id == 1 else (0, 255, 0)

                        scale = 1.0 / CAPTURE_SCALE
                        sx1 = int(x1 * scale)
                        sy1 = int(y1 * scale)
                        sx2 = int(x2 * scale)
                        sy2 = int(y2 * scale)

                        boxes_list.append((sx1, sy1, sx2, sy2, label, color))

                self.last_boxes = boxes_list.copy()

                self.fps_counter += 1
                now = time.time()
                if now - self.fps_last_time >= 1.0:
                    self.fps = self.fps_counter / (now - self.fps_last_time)
                    self.fps_updated.emit(self.fps, CAPTURE_SCALE, DET_IMG_SIZE, FRAME_SKIP)
                    self.fps_counter = 0
                    self.fps_last_time = now

                self.results_ready.emit(boxes_list, frame.shape[1], frame.shape[0])
                self.msleep(1)
        except Exception as e:
            print(f"DetectorThread error: {e}")
            traceback.print_exc()
        finally:
            print("DetectorThread finished")

class OverlayWidget(QOpenGLWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.boxes = []
        self.fps = 0.0
        self.cap_scale = CAPTURE_SCALE
        self.img_size = DET_IMG_SIZE
        self.skip = FRAME_SKIP
        self.screen_width = parent.width()
        self.screen_height = parent.height()

    def update_boxes(self, boxes):
        self.boxes = boxes
        self.update()

    def update_stats(self, fps, cap_scale, img_size, skip):
        self.fps = fps
        self.cap_scale = cap_scale
        self.img_size = img_size
        self.skip = skip
        self.update()

    def paintGL(self):
        gl.glClearColor(0.0, 0.0, 0.0, 0.0)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        painter.setFont(QFont("Arial", 12))
        for (x1, y1, x2, y2, label, color) in self.boxes:
            painter.setPen(QPen(QColor(*color), 3))
            painter.drawRect(x1, y1, x2 - x1, y2 - y1)
            painter.setPen(QPen(QColor(255, 255, 255), 1))
            painter.drawText(x1, y1 - 5, label)

        painter.setPen(QPen(QColor(255, 255, 0), 2))
        painter.setFont(QFont("Arial", 14, QFont.Bold))
        painter.drawText(10, 30, f"FPS: {self.fps:.1f}")
        painter.setFont(QFont("Arial", 10))
        painter.drawText(10, 55, f"Scale: {self.cap_scale:.2f} | Size: {self.img_size} | Skip: {self.skip}")
        painter.drawText(10, 80, f"Objects: {len(self.boxes)}")

        painter.end()

class OverlaySettingsDialog(QDialog):
    def __init__(self, overlay_window, parent=None):
        super().__init__(parent, Qt.WindowStaysOnTopHint)
        self.overlay = overlay_window
        self.setWindowTitle(tr("Настройки оверлея"))
        self.setFixedSize(300, 280)
        layout = QVBoxLayout(self)

        # Capture scale
        layout.addWidget(QLabel(tr("Масштаб захвата:")))
        self.scale_slider = QSlider(Qt.Horizontal)
        self.scale_slider.setRange(10, 100)
        self.scale_slider.setValue(int(overlay_window.capture_thread.scale * 100))
        self.scale_slider.valueChanged.connect(self.on_scale_changed)
        layout.addWidget(self.scale_slider)
        self.scale_label = QLabel(f"{overlay_window.capture_thread.scale:.2f}")
        layout.addWidget(self.scale_label)

        # Image size
        layout.addWidget(QLabel(tr("Размер изображения для детекции:")))
        self.imgsz_spin = QSpinBox()
        self.imgsz_spin.setRange(320, 1280)
        self.imgsz_spin.setValue(overlay_window.detector_thread.imgsz)
        self.imgsz_spin.valueChanged.connect(self.on_imgsz_changed)
        layout.addWidget(self.imgsz_spin)

        # Frame skip
        layout.addWidget(QLabel(tr("Пропуск кадров:")))
        self.skip_spin = QSpinBox()
        self.skip_spin.setRange(1, 10)
        self.skip_spin.setValue(overlay_window.detector_thread.frame_skip)
        self.skip_spin.valueChanged.connect(self.on_skip_changed)
        layout.addWidget(self.skip_spin)

        # Show tracks
        self.tracks_check = QCheckBox(tr("Показывать треки"))
        self.tracks_check.setChecked(SHOW_TRACKS)
        self.tracks_check.toggled.connect(self.on_tracks_toggled)
        layout.addWidget(self.tracks_check)

        # Кнопка закрытия оверлея (альтернатива горячей клавише)
        btn_close_overlay = QPushButton(tr("Закрыть оверлей"))
        btn_close_overlay.clicked.connect(self.overlay.close)
        layout.addWidget(btn_close_overlay)

        # Close settings button
        btn_close = QPushButton(tr("Закрыть настройки"))
        btn_close.clicked.connect(self.close)
        layout.addWidget(btn_close)

    def on_scale_changed(self, value):
        scale = value / 100.0
        self.scale_label.setText(f"{scale:.2f}")
        self.overlay.capture_thread.scale = scale
        global CAPTURE_SCALE
        CAPTURE_SCALE = scale

    def on_imgsz_changed(self, value):
        self.overlay.detector_thread.imgsz = value
        global DET_IMG_SIZE
        DET_IMG_SIZE = value

    def on_skip_changed(self, value):
        self.overlay.detector_thread.frame_skip = value
        global FRAME_SKIP
        FRAME_SKIP = value

    def on_tracks_toggled(self, checked):
        global SHOW_TRACKS
        SHOW_TRACKS = checked

class OverlayWindow(QMainWindow):
    def __init__(self, detector=None, classifier=None):
        if detector is None:
            raise ValueError("Detector model is required for overlay")
        super().__init__()
        self.detector = detector
        self.classifier = classifier
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)

        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen)
        self.screen_width = screen.width()
        self.screen_height = screen.height()

        self.widget = OverlayWidget(self)
        self.setCentralWidget(self.widget)

        self.apply_win32_overlay_style()

        self.capture_thread = CaptureThread(scale=CAPTURE_SCALE)
        self.detector_thread = DetectorThread(detector, classifier, self.capture_thread)
        self.detector_thread.results_ready.connect(self.widget.update_boxes)
        self.detector_thread.fps_updated.connect(self.widget.update_stats)

        self.key_timer = QTimer()
        self.key_timer.timeout.connect(self.check_keys)
        self.key_timer.start(50)

        self.settings_dialog = None

        self.capture_thread.start()
        self.detector_thread.start()

    def apply_win32_overlay_style(self):
        try:
            hwnd = int(self.winId())
            GWL_EXSTYLE = -20
            WS_EX_TRANSPARENT = 0x00000020
            WS_EX_LAYERED = 0x00080000
            WS_EX_NOACTIVATE = 0x08000000
            WS_EX_TOPMOST = 0x00000008

            current_style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            new_style = current_style | WS_EX_TRANSPARENT | WS_EX_LAYERED | WS_EX_NOACTIVATE | WS_EX_TOPMOST
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, new_style)

            ctypes.windll.user32.EnableWindow(hwnd, False)

            class DWM_BLURBEHIND(ctypes.Structure):
                _fields_ = [
                    ("dwFlags", ctypes.c_ulong),
                    ("fEnable", ctypes.c_bool),
                    ("hRgnBlur", ctypes.c_void_p),
                    ("fTransitionOnMaximized", ctypes.c_bool)
                ]
            DWM_BB_ENABLE = 0x00000001
            DWM_BB_BLURREGION = 0x00000002

            hrgn = ctypes.windll.gdi32.CreateRectRgn(0, 0, -1, -1)
            bb = DWM_BLURBEHIND()
            bb.dwFlags = DWM_BB_ENABLE | DWM_BB_BLURREGION
            bb.fEnable = True
            bb.hRgnBlur = hrgn
            bb.fTransitionOnMaximized = False

            dwm_api = ctypes.windll.dwmapi
            dwm_api.DwmEnableBlurBehindWindow(hwnd, ctypes.byref(bb))
            print("[WinAPI] Overlay style applied.")
        except Exception as e:
            print(f"[WinAPI] Error: {e}")

    def safe_is_pressed(self, key):
        try:
            import keyboard
            return keyboard.is_pressed(key)
        except:
            return False

    def open_settings(self):
        if self.settings_dialog is None:
            self.settings_dialog = OverlaySettingsDialog(self)
            self.settings_dialog.show()
        else:
            self.settings_dialog.raise_()
            self.settings_dialog.activateWindow()

    def check_keys(self):
        global CAPTURE_SCALE, DET_IMG_SIZE, FRAME_SKIP, SHOW_TRACKS
        try:
            if self.safe_is_pressed('q'):
                self.close()
            elif self.safe_is_pressed('o'):
                self.open_settings()
            elif self.safe_is_pressed('k'):
                self.detector_thread.classifier_enabled = not self.detector_thread.classifier_enabled
                print(f"Classifier enabled: {self.detector_thread.classifier_enabled}")
            elif self.safe_is_pressed('p'):
                self.save_screenshot()
            elif self.safe_is_pressed('l'):
                self.save_annotation()
            elif self.safe_is_pressed('t'):
                SHOW_TRACKS = not SHOW_TRACKS
                print(f"Show tracks: {SHOW_TRACKS}")

            if self.safe_is_pressed('='):
                CAPTURE_SCALE = min(1.0, CAPTURE_SCALE + 0.1)
                self.capture_thread.scale = CAPTURE_SCALE
                print(f"CAPTURE_SCALE = {CAPTURE_SCALE:.2f}")
            elif self.safe_is_pressed('-'):
                CAPTURE_SCALE = max(0.1, CAPTURE_SCALE - 0.1)
                self.capture_thread.scale = CAPTURE_SCALE
                print(f"CAPTURE_SCALE = {CAPTURE_SCALE:.2f}")
            elif self.safe_is_pressed('m'):
                DET_IMG_SIZE = min(1280, DET_IMG_SIZE + 64)
                self.detector_thread.imgsz = DET_IMG_SIZE
                print(f"DET_IMG_SIZE = {DET_IMG_SIZE}")
            elif self.safe_is_pressed('n'):
                DET_IMG_SIZE = max(320, DET_IMG_SIZE - 64)
                self.detector_thread.imgsz = DET_IMG_SIZE
                print(f"DET_IMG_SIZE = {DET_IMG_SIZE}")
            elif self.safe_is_pressed('.'):
                FRAME_SKIP = min(10, FRAME_SKIP + 1)
                self.detector_thread.frame_skip = FRAME_SKIP
                print(f"FRAME_SKIP = {FRAME_SKIP}")
            elif self.safe_is_pressed(','):
                FRAME_SKIP = max(1, FRAME_SKIP - 1)
                self.detector_thread.frame_skip = FRAME_SKIP
                print(f"FRAME_SKIP = {FRAME_SKIP}")
            elif self.safe_is_pressed('r'):
                CAPTURE_SCALE = 0.5
                DET_IMG_SIZE = 640
                FRAME_SKIP = 2
                self.capture_thread.scale = CAPTURE_SCALE
                self.detector_thread.imgsz = DET_IMG_SIZE
                self.detector_thread.frame_skip = FRAME_SKIP
                print("Settings reset")
        except Exception as e:
            print(f"Key error: {e}")

    def save_screenshot(self):
        boxes = self.detector_thread.last_boxes
        if not boxes:
            print("No boxes to save")
            return
        with mss.mss() as sct:
            monitor = sct.monitors[1]
            img = sct.grab(monitor)
            frame = cv2.cvtColor(np.array(img), cv2.COLOR_BGRA2BGR)
            for (x1, y1, x2, y2, label, color) in boxes:
                bgr_color = (0,0,255) if color == (255,0,0) else (0,255,0)
                cv2.rectangle(frame, (x1, y1), (x2, y2), bgr_color, 2)
                frame = draw_text_cv2(frame, label, (x1, y1-10), color=bgr_color, font_scale=0.5)
            filename = f"detection_{time.strftime('%Y%m%d_%H%M%S')}.jpg"
            cv2.imwrite(filename, frame)
            print(f"Saved: {filename}")

    def save_annotation(self):
        boxes = self.detector_thread.last_boxes
        if not boxes:
            print("No boxes to save")
            return
        with mss.mss() as sct:
            monitor = sct.monitors[1]
            img = sct.grab(monitor)
            frame = cv2.cvtColor(np.array(img), cv2.COLOR_BGRA2BGR)
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            img_filename = f"auto_{timestamp}.jpg"

            # Save captures to BASE_DIR/data/overlay_captures/ (no longer tied to config.AUTO_JSON)
            capture_dir = os.path.join(config.BASE_DIR, "data", "overlay_captures")
            os.makedirs(capture_dir, exist_ok=True)
            img_path = os.path.join(capture_dir, img_filename)
            cv2.imwrite(img_path, frame)

            ann_file = os.path.join(capture_dir, "annotations.json")
            if os.path.exists(ann_file):
                try:
                    with open(ann_file, 'r', encoding='utf-8') as f:
                        annotations = json.load(f)
                except Exception:
                    annotations = {}
            else:
                annotations = {}

            boxes_list = []
            for (x1, y1, x2, y2, label, color) in boxes:
                parts = label.split()
                obj_str = tr("объект")
                tank_type = parts[0] if parts[0] != obj_str else obj_str
                boxes_list.append({
                    "bbox": [x1, y1, x2, y2],
                    "class": tank_type
                })
            annotations[img_filename] = boxes_list
            with open(ann_file, 'w', encoding='utf-8') as f:
                json.dump(annotations, f, indent=2, ensure_ascii=False)
            print(f"Saved {len(boxes_list)} boxes to {img_path}")

    def closeEvent(self, event):
        self.capture_thread.stop()
        self.detector_thread.stop()
        self.capture_thread.wait()
        self.detector_thread.wait()
        if self.settings_dialog:
            self.settings_dialog.close()
        event.accept()