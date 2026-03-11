from collections import deque
from PyQt5.QtWidgets import QOpenGLWidget
from PyQt5.QtCore import Qt, QRect, pyqtSignal
from PyQt5.QtGui import QPainter, QPen, QColor, QImage, QPixmap

class AnnotationWidget(QOpenGLWidget):
    selection_changed = pyqtSignal(int)
    status_message = pyqtSignal(str)
    boxes_changed = pyqtSignal()
    show_type_dialog_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.image_orig = None
        self.pixmap = None
        self.boxes = []
        self.selected_idx = -1
        self.current_class = "unknown"
        self.available_classes = ["unknown"]
        self.class_colors = {}  # class -> QColor name

        self.zoom = 1.0
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.last_mouse_pos = None
        self.panning = False

        self.drawing = False
        self.drag_start = None
        self.drag_end = None
        self.dragging_box = False
        self.drag_box_idx = -1
        self.drag_start_pos = None
        self.original_box = None
        self.resize_mode = None
        self.resize_start_pos = None

        self.history = deque(maxlen=50)
        self.history_enabled = True

        self.detector = None
        self.classifier = None

        self.setAutoFillBackground(True)
        self.setFocusPolicy(Qt.StrongFocus)

    def set_image(self, img_np):
        self.image_orig = img_np.copy()
        h, w, ch = self.image_orig.shape
        bytes_per_line = ch * w
        qimage = QImage(self.image_orig.data, w, h, bytes_per_line, QImage.Format_RGB888)
        self.pixmap = QPixmap.fromImage(qimage)
        self.update()

    def set_boxes(self, boxes):
        self.boxes = boxes
        self.boxes_changed.emit()
        self.update()

    def set_classes(self, classes_list, current_class):
        self.available_classes = classes_list
        self.current_class = current_class
        self.update()

    def set_models(self, detector=None, classifier=None):
        self.detector = detector
        self.classifier = classifier

    def screen_to_image(self, x, y):
        return (x - self.pan_x) / self.zoom, (y - self.pan_y) / self.zoom

    def image_to_screen(self, x, y):
        return int(x * self.zoom + self.pan_x), int(y * self.zoom + self.pan_y)

    def initializeGL(self):
        pass

    def resizeGL(self, w, h):
        pass

    def paintGL(self):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        painter.fillRect(self.rect(), QColor(50, 50, 50))

        if self.pixmap and not self.pixmap.isNull():
            target_rect = QRect(
                int(self.pan_x),
                int(self.pan_y),
                int(self.pixmap.width() * self.zoom),
                int(self.pixmap.height() * self.zoom)
            )
            painter.drawPixmap(target_rect, self.pixmap)

            for idx, box in enumerate(self.boxes):
                x1, y1, x2, y2 = box["bbox"]
                sx1, sy1 = self.image_to_screen(x1, y1)
                sx2, sy2 = self.image_to_screen(x2, y2)
                if sx2 < sx1: sx1, sx2 = sx2, sx1
                if sy2 < sy1: sy1, sy2 = sy2, sy1
                if sx2 - sx1 < 1 or sy2 - sy1 < 1:
                    continue
                # Определяем цвет
                class_name = box.get("class", "unknown")
                color_name = self.class_colors.get(class_name, "#ff0000")  # по умолчанию красный
                color = QColor(color_name)
                if idx == self.selected_idx:
                    painter.setPen(QPen(QColor(0, 255, 255), 3))
                    painter.setBrush(QColor(0, 255, 255, 50))
                else:
                    painter.setPen(QPen(color, 2))
                    painter.setBrush(Qt.NoBrush)
                painter.drawRect(QRect(sx1, sy1, sx2 - sx1, sy2 - sy1))
                painter.setPen(QPen(QColor(255, 255, 255), 1))
                painter.drawText(sx1, sy1 - 5, class_name)

            if self.drawing and self.drag_start and self.drag_end:
                x1, y1 = self.drag_start
                x2, y2 = self.drag_end
                sx1, sy1 = self.image_to_screen(x1, y1)
                sx2, sy2 = self.image_to_screen(x2, y2)
                if sx2 < sx1: sx1, sx2 = sx2, sx1
                if sy2 < sy1: sy1, sy2 = sy2, sy1
                painter.setPen(QPen(QColor(0, 255, 0), 2))
                painter.setBrush(Qt.NoBrush)
                painter.drawRect(QRect(sx1, sy1, sx2 - sx1, sy2 - sy1))
                painter.drawText(sx1, sy1 - 5, self.current_class)
        else:
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(10, 20, "Нет изображения")

        painter.end()

    def wheelEvent(self, event):
        factor = 1.1
        if event.angleDelta().y() < 0:
            factor = 1.0 / factor
        mouse_x, mouse_y = event.x(), event.y()
        img_x, img_y = self.screen_to_image(mouse_x, mouse_y)
        self.zoom *= factor
        self.zoom = max(0.1, min(10.0, self.zoom))
        new_img_x, new_img_y = self.screen_to_image(mouse_x, mouse_y)
        self.pan_x += (new_img_x - img_x) * self.zoom
        self.pan_y += (new_img_y - img_y) * self.zoom
        self.update()

    def mousePressEvent(self, event):
        if self.image_orig is None:
            return

        if event.button() == Qt.RightButton:
            x, y = self.screen_to_image(event.x(), event.y())
            if 0 <= x < self.image_orig.shape[1] and 0 <= y < self.image_orig.shape[0]:
                self.show_type_dialog_requested.emit()
            return

        if event.button() == Qt.MiddleButton:
            self.panning = True
            self.last_mouse_pos = event.pos()
            return

        if event.button() == Qt.LeftButton:
            x, y = self.screen_to_image(event.x(), event.y())
            if x < 0 or y < 0 or x >= self.image_orig.shape[1] or y >= self.image_orig.shape[0]:
                return

            if self.drawing:
                self.drag_start = (x, y)
                self.drag_end = (x, y)
                self.update()
                return

            if self.selected_idx >= 0 and self.selected_idx < len(self.boxes):
                box = self.boxes[self.selected_idx]
                x1, y1, x2, y2 = box["bbox"]
                sx1, sy1 = self.image_to_screen(x1, y1)
                sx2, sy2 = self.image_to_screen(x2, y2)
                tol = 10
                ex, ey = event.x(), event.y()
                if abs(ex - sx1) < tol and abs(ey - sy1) < tol:
                    self.resize_mode = 'tl'
                elif abs(ex - sx2) < tol and abs(ey - sy1) < tol:
                    self.resize_mode = 'tr'
                elif abs(ex - sx1) < tol and abs(ey - sy2) < tol:
                    self.resize_mode = 'bl'
                elif abs(ex - sx2) < tol and abs(ey - sy2) < tol:
                    self.resize_mode = 'br'
                elif abs(ex - sx1) < tol and sy1 <= ey <= sy2:
                    self.resize_mode = 'left'
                elif abs(ex - sx2) < tol and sy1 <= ey <= sy2:
                    self.resize_mode = 'right'
                elif abs(ey - sy1) < tol and sx1 <= ex <= sx2:
                    self.resize_mode = 'top'
                elif abs(ey - sy2) < tol and sx1 <= ex <= sx2:
                    self.resize_mode = 'bottom'

                if self.resize_mode:
                    self.save_state_to_history()
                    self.resize_start_pos = (x, y)
                    self.original_box = (x1, y1, x2, y2)
                    return

            for idx, box in enumerate(self.boxes):
                x1, y1, x2, y2 = box["bbox"]
                if x1 <= x <= x2 and y1 <= y <= y2:
                    self.save_state_to_history()
                    self.dragging_box = True
                    self.drag_box_idx = idx
                    self.drag_start_pos = (x, y)
                    self.original_box = (x1, y1, x2, y2)
                    self.selected_idx = idx
                    self.selection_changed.emit(idx)
                    self.update()
                    return

            self.save_state_to_history()
            self.drawing = True
            self.drag_start = (x, y)
            self.drag_end = (x, y)
            self.update()

    def mouseMoveEvent(self, event):
        if self.image_orig is None:
            return

        if self.panning:
            dx = event.x() - self.last_mouse_pos.x()
            dy = event.y() - self.last_mouse_pos.y()
            self.pan_x += dx
            self.pan_y += dy
            self.last_mouse_pos = event.pos()
            self.update()
            return

        x, y = self.screen_to_image(event.x(), event.y())
        if x < 0 or y < 0 or x >= self.image_orig.shape[1] or y >= self.image_orig.shape[0]:
            return

        if self.resize_mode and self.resize_start_pos and self.original_box:
            dx = x - self.resize_start_pos[0]
            dy = y - self.resize_start_pos[1]
            x1, y1, x2, y2 = self.original_box
            if self.resize_mode == 'tl':
                new_x1 = x1 + dx
                new_y1 = y1 + dy
                new_x2 = x2
                new_y2 = y2
            elif self.resize_mode == 'tr':
                new_x1 = x1
                new_y1 = y1 + dy
                new_x2 = x2 + dx
                new_y2 = y2
            elif self.resize_mode == 'bl':
                new_x1 = x1 + dx
                new_y1 = y1
                new_x2 = x2
                new_y2 = y2 + dy
            elif self.resize_mode == 'br':
                new_x1 = x1
                new_y1 = y1
                new_x2 = x2 + dx
                new_y2 = y2 + dy
            elif self.resize_mode == 'left':
                new_x1 = x1 + dx
                new_x2 = x2
                new_y1 = y1
                new_y2 = y2
            elif self.resize_mode == 'right':
                new_x1 = x1
                new_x2 = x2 + dx
                new_y1 = y1
                new_y2 = y2
            elif self.resize_mode == 'top':
                new_x1 = x1
                new_x2 = x2
                new_y1 = y1 + dy
                new_y2 = y2
            elif self.resize_mode == 'bottom':
                new_x1 = x1
                new_x2 = x2
                new_y1 = y1
                new_y2 = y2 + dy

            h, w, _ = self.image_orig.shape
            new_x1 = round(new_x1)
            new_y1 = round(new_y1)
            new_x2 = round(new_x2)
            new_y2 = round(new_y2)

            if new_x1 < 0: new_x1 = 0
            if new_y1 < 0: new_y1 = 0
            if new_x2 > w: new_x2 = w
            if new_y2 > h: new_y2 = h
            if new_x2 - new_x1 < 5: new_x2 = new_x1 + 5
            if new_y2 - new_y1 < 5: new_y2 = new_y1 + 5

            if self.selected_idx >= 0:
                self.boxes[self.selected_idx]["bbox"] = [new_x1, new_y1, new_x2, new_y2]
                self.boxes_changed.emit()
                self.update()
            return

        if self.dragging_box and self.drag_start_pos and self.original_box:
            dx = x - self.drag_start_pos[0]
            dy = y - self.drag_start_pos[1]
            x1, y1, x2, y2 = self.original_box
            new_x1 = round(x1 + dx)
            new_y1 = round(y1 + dy)
            new_x2 = round(x2 + dx)
            new_y2 = round(y2 + dy)

            h, w, _ = self.image_orig.shape
            if new_x1 < 0:
                new_x2 -= new_x1
                new_x1 = 0
            if new_y1 < 0:
                new_y2 -= new_y1
                new_y1 = 0
            if new_x2 > w:
                new_x1 -= (new_x2 - w)
                new_x2 = w
            if new_y2 > h:
                new_y1 -= (new_y2 - h)
                new_y2 = h
            if new_x2 - new_x1 < 5 or new_y2 - new_y1 < 5:
                return
            if self.drag_box_idx >= 0:
                self.boxes[self.drag_box_idx]["bbox"] = [new_x1, new_y1, new_x2, new_y2]
                self.boxes_changed.emit()
                self.update()
            return

        if self.drawing:
            self.drag_end = (x, y)
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MiddleButton:
            self.panning = False
            return
        if event.button() == Qt.LeftButton:
            if self.resize_mode:
                self.resize_mode = None
                self.resize_start_pos = None
                self.original_box = None
                self.boxes_changed.emit()
                return
            if self.dragging_box:
                self.dragging_box = False
                self.drag_box_idx = -1
                self.drag_start_pos = None
                self.original_box = None
                self.boxes_changed.emit()
                return
            if self.drawing:
                if self.drag_start and self.drag_end:
                    x1 = round(min(self.drag_start[0], self.drag_end[0]))
                    y1 = round(min(self.drag_start[1], self.drag_end[1]))
                    x2 = round(max(self.drag_start[0], self.drag_end[0]))
                    y2 = round(max(self.drag_start[1], self.drag_end[1]))
                    if x2 - x1 > 5 and y2 - y1 > 5:
                        new_box = {"bbox": [x1, y1, x2, y2], "class": self.current_class}
                        self.boxes.append(new_box)
                        self.selected_idx = len(self.boxes) - 1
                        self.selection_changed.emit(self.selected_idx)
                        self.status_message.emit(f"Добавлен бокс класса {self.current_class}")
                        self.boxes_changed.emit()
                self.drawing = False
                self.drag_start = None
                self.drag_end = None
                self.update()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Delete and self.selected_idx >= 0:
            self.delete_selected()
        elif event.modifiers() & Qt.ControlModifier and event.key() == Qt.Key_Z:
            self.undo()
        elif event.key() == Qt.Key_S:
            self.emit_status("Сохранить (авто)")
        elif event.key() == Qt.Key_N:
            self.start_drawing()
        else:
            super().keyPressEvent(event)

    def start_drawing(self):
        self.drawing = True
        self.drag_start = None
        self.drag_end = None
        self.status_message.emit("Рисуйте новый бокс")

    def delete_selected(self):
        if self.selected_idx >= 0 and self.selected_idx < len(self.boxes):
            self.save_state_to_history()
            del self.boxes[self.selected_idx]
            self.selected_idx = -1
            self.selection_changed.emit(-1)
            self.boxes_changed.emit()
            self.update()

    def save_state_to_history(self):
        if not self.history_enabled:
            return
        state = [box.copy() for box in self.boxes]
        self.history.append(state)

    def undo(self):
        if not self.history:
            self.status_message.emit("Нечего отменять")
            return
        prev = self.history.pop()
        self.boxes = [box.copy() for box in prev]
        self.selected_idx = -1
        self.selection_changed.emit(-1)
        self.boxes_changed.emit()
        self.update()

    def emit_status(self, msg):
        self.status_message.emit(msg)

    def auto_annotate(self, conf_threshold=0.25, iou_threshold=0.5, cls_conf=0.5):
        if self.detector is None:
            self.status_message.emit("Детектор не загружен")
            return
        if self.image_orig is None:
            return
        self.status_message.emit("Авторазметка...")
        try:
            results = self.detector(self.image_orig, conf=conf_threshold, iou=iou_threshold, verbose=False)[0]
            boxes = results.boxes
            if boxes is None or len(boxes) == 0:
                self.status_message.emit("Ничего не найдено")
                return
            self.save_state_to_history()
            new_boxes = []
            for box in boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                class_name = "unknown"
                if self.classifier is not None:
                    crop = self.image_orig[y1:y2, x1:x2]
                    if crop.size > 0:
                        cls_results = self.classifier(crop, verbose=False)
                        probs = cls_results[0].probs
                        if probs is not None:
                            top_conf = probs.top1conf.item()
                            top_class_id = probs.top1
                            if top_conf >= cls_conf:
                                class_name = self.classifier.names[top_class_id]
                new_boxes.append({"bbox": [x1, y1, x2, y2], "class": class_name})
            self.boxes.extend(new_boxes)
            self.boxes_changed.emit()
            self.status_message.emit(f"Добавлено {len(new_boxes)} боксов")
            self.update()
        except Exception as e:
            self.status_message.emit(f"Ошибка авторазметки: {e}")