from collections import deque
import copy
import logging
from PyQt5.QtWidgets import QOpenGLWidget
from PyQt5.QtCore import Qt, QRect, pyqtSignal
from PyQt5.QtGui import QPainter, QPen, QColor, QImage, QPixmap, QPolygon
from PyQt5.QtCore import QPoint
from core.i18n import tr
from core.smart_segmenter import SmartSegmenter

logging.basicConfig(filename='visionforge.log', level=logging.ERROR,
                    format='%(asctime)s - %(levelname)s - %(message)s')

def get_contrast_text_color(bg_color):
    """Возвращает чёрный или белый цвет в зависимости от яркости фона."""
    brightness = (bg_color.red() * 299 + bg_color.green() * 587 + bg_color.blue() * 114) / 1000
    return Qt.black if brightness > 128 else Qt.white

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
        self.class_colors = {}

        self.zoom = 1.0
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.last_mouse_pos = None
        self.panning = False

        # Режим рисования: 'box' или 'polygon'
        self.draw_mode = 'box'
        self.drawing = False
        self.drag_start = None
        self.drag_end = None
        self.dragging_temp_point_idx = -1
        self.dragging_box = False
        self.drag_box_idx = -1
        self.drag_start_pos = None
        self.original_box = None
        self.original_polygon = None
        self.resize_mode = None
        self.resize_start_pos = None

        # Полигон: текущие точки при рисовании
        self.polygon_points = []
        self.dragging_point_idx = -1
        self.drag_polygon_idx = -1

        # Состояние «призрачной» точки при зажатой ЛКМ в режиме полигона
        self._poly_ghost_pos = None   # (x, y) в координатах изображения — превью при зажатой мыши
        self._poly_press_hit_idx = -1 # индекс точки под курсором при нажатии (-1 = пусто)

        self.history = deque(maxlen=100)
        self.history_enabled = True

        self.detector = None
        self.classifier = None
        self.smart_segmenter = SmartSegmenter()

        self.setAutoFillBackground(True)
        self.setFocusPolicy(Qt.StrongFocus)

    def set_image(self, img_np):
        self.image_orig = img_np.copy()
        h, w, ch = self.image_orig.shape
        bytes_per_line = ch * w
        # GC fix: .copy() transfers ownership so NumPy buffer won't be freed
        # while QImage / QPixmap is still referencing it
        qimage = QImage(self.image_orig.data, w, h, bytes_per_line,
                        QImage.Format_RGB888).copy()
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
        if hasattr(self, 'smart_segmenter') and self.smart_segmenter is not None:
            self.smart_segmenter.model = detector

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

        painter.fillRect(self.rect(), QColor(16, 16, 20))

        if self.pixmap and not self.pixmap.isNull():
            target_rect = QRect(
                int(self.pan_x),
                int(self.pan_y),
                int(self.pixmap.width() * self.zoom),
                int(self.pixmap.height() * self.zoom)
            )
            painter.drawPixmap(target_rect, self.pixmap)

            for idx, box in enumerate(self.boxes):
                class_name = box.get("class", "unknown")
                color_name = self.class_colors.get(class_name, "#818cf8")
                color = QColor(color_name)

                if idx == self.selected_idx:
                    painter.setPen(QPen(QColor(99, 102, 241), 3))
                    painter.setBrush(QColor(99, 102, 241, 40))
                else:
                    painter.setPen(QPen(color, 2))
                    painter.setBrush(Qt.NoBrush)

                if "polygon" in box and box["polygon"]:
                    # Рисуем полигон
                    points = []
                    for pt in box["polygon"]:
                        sx, sy = self.image_to_screen(pt[0], pt[1])
                        points.append(QPoint(sx, sy))
                    if points:
                        polygon = QPolygon(points)
                        painter.drawPolygon(polygon)
                        
                        # Плашка класса
                        lx, ly = points[0].x(), points[0].y() - 6
                        painter.setPen(Qt.NoPen)
                        painter.setBrush(QColor(24, 24, 28, 200))
                        painter.drawRoundedRect(QRect(lx - 2, ly - 13, len(class_name) * 7 + 8, 15), 3, 3)
                        painter.setPen(QPen(color if idx != self.selected_idx else QColor(129, 140, 248), 1))
                        painter.drawText(lx + 2, ly, class_name)
                elif "bbox" in box:
                    x1, y1, x2, y2 = box["bbox"]
                    sx1, sy1 = self.image_to_screen(x1, y1)
                    sx2, sy2 = self.image_to_screen(x2, y2)
                    if sx2 < sx1: sx1, sx2 = sx2, sx1
                    if sy2 < sy1: sy1, sy2 = sy2, sy1
                    if sx2 - sx1 < 1 or sy2 - sy1 < 1:
                        continue
                    painter.drawRect(QRect(sx1, sy1, sx2 - sx1, sy2 - sy1))
                    
                    # Плашка класса
                    lx, ly = sx1, sy1 - 4
                    painter.setPen(Qt.NoPen)
                    painter.setBrush(QColor(24, 24, 28, 200))
                    painter.drawRoundedRect(QRect(lx - 2, ly - 13, len(class_name) * 7 + 8, 15), 3, 3)
                    painter.setPen(QPen(color if idx != self.selected_idx else QColor(129, 140, 248), 1))
                    painter.drawText(lx + 2, ly, class_name)

                # Рисуем ручки для углов бокса или точек полигона у выбранного объекта
                if idx == self.selected_idx:
                    if "polygon" in box and box["polygon"]:
                        painter.setBrush(QColor(0, 255, 255))
                        for pt in box["polygon"]:
                            sx, sy = self.image_to_screen(pt[0], pt[1])
                            painter.drawEllipse(QPoint(sx, sy), 5, 5)
                        painter.setBrush(Qt.NoBrush)
                    elif "bbox" in box:
                        x1, y1, x2, y2 = box["bbox"]
                        for bx, by in [(x1, y1), (x2, y1), (x1, y2), (x2, y2)]:
                            sx, sy = self.image_to_screen(bx, by)
                            painter.setBrush(QColor(0, 255, 255))
                            painter.drawEllipse(QPoint(sx, sy), 4, 4)
                        painter.setBrush(Qt.NoBrush)

            # Рисуем текущий бокс при перетаскивании
            if self.drawing and self.draw_mode == 'box' and self.drag_start and self.drag_end:
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

            # Рисуем текущий полигон при создании
            if self.polygon_points or self._poly_ghost_pos:
                painter.setPen(QPen(QColor(0, 255, 0), 2))
                painter.setBrush(Qt.NoBrush)
                screen_pts = []
                for pt in self.polygon_points:
                    sx, sy = self.image_to_screen(pt[0], pt[1])
                    screen_pts.append(QPoint(sx, sy))

                # «Призрачная» точка при зажатой мыши (превью до отпускания)
                ghost_sp = None
                if self._poly_ghost_pos is not None and self._poly_press_hit_idx < 0:
                    gx, gy = self.image_to_screen(self._poly_ghost_pos[0], self._poly_ghost_pos[1])
                    ghost_sp = QPoint(gx, gy)

                # Линии между зафиксированными точками
                for i in range(len(screen_pts) - 1):
                    painter.drawLine(screen_pts[i], screen_pts[i + 1])

                # Линия от последней точки к призраку
                if ghost_sp and screen_pts:
                    painter.setPen(QPen(QColor(0, 255, 0, 150), 1, Qt.DashLine))
                    painter.drawLine(screen_pts[-1], ghost_sp)
                    painter.setPen(QPen(QColor(0, 255, 0), 2))

                # Рисуем зафиксированные точки
                for i, sp in enumerate(screen_pts):
                    if i == 0 and len(screen_pts) >= 3:
                        # Первая точка — подсветка «закрыть полигон»
                        painter.setBrush(QColor(255, 200, 0))
                        painter.drawEllipse(sp, 6, 6)
                    else:
                        painter.setBrush(QColor(0, 255, 0))
                        painter.drawEllipse(sp, 4, 4)
                    painter.setBrush(Qt.NoBrush)

                # Рисуем призрачную точку (полупрозрачная)
                if ghost_sp:
                    painter.setBrush(QColor(0, 255, 0, 120))
                    painter.setPen(QPen(QColor(0, 255, 0, 180), 1))
                    painter.drawEllipse(ghost_sp, 4, 4)
                    painter.setBrush(Qt.NoBrush)
                    painter.setPen(QPen(QColor(0, 255, 0), 2))

                if screen_pts:
                    painter.drawText(screen_pts[0].x(), screen_pts[0].y() - 5, self.current_class)
        else:
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(10, 20, tr("Нет изображения"))

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

            # Режим «Магия» (1-клик сегментация FastSAM / GrabCut)
            if self.draw_mode == 'magic':
                self.save_state_to_history()
                poly_pts = self.smart_segmenter.segment_point(self.image_orig, round(x), round(y))
                if poly_pts and len(poly_pts) >= 3:
                    xs = [p[0] for p in poly_pts]
                    ys = [p[1] for p in poly_pts]
                    bbox = [min(xs), min(ys), max(xs), max(ys)]
                    new_obj = {
                        "bbox": bbox,
                        "polygon": poly_pts,
                        "class": self.current_class
                    }
                    self.boxes.append(new_obj)
                    self.selected_idx = len(self.boxes) - 1
                    self.boxes_changed.emit()
                    self.status_message.emit(f"{tr('Добавлен полигон класса')} {self.current_class} ({len(poly_pts)} {tr('точек')})")
                    self.update()
                else:
                    self.status_message.emit(tr("Не удалось выделить объект. Попробуйте кликнуть ближе к центру."))
                return

            # Режим полигона: при нажатии определяем — попали ли в точку
            if self.draw_mode == 'polygon' and self.drawing:
                tol = 12
                self._poly_press_hit_idx = -1
                for p_idx, pt in enumerate(self.polygon_points):
                    sx, sy = self.image_to_screen(pt[0], pt[1])
                    if abs(event.x() - sx) < tol and abs(event.y() - sy) < tol:
                        if p_idx == 0 and len(self.polygon_points) >= 3:
                            # Нажали на первую точку — закроем полигон при отпускании
                            self._poly_press_hit_idx = 0
                        else:
                            # Нажали на существующую точку — начинаем перетаскивание
                            self._poly_press_hit_idx = p_idx
                            self.dragging_temp_point_idx = p_idx
                        break

                # Показываем призрак только если не попали в точку
                if self._poly_press_hit_idx < 0:
                    self._poly_ghost_pos = (round(x), round(y))
                self.update()
                return

            if self.drawing and self.draw_mode == 'box':
                self.drag_start = (x, y)
                self.drag_end = (x, y)
                self.update()
                return

            if 0 <= self.selected_idx < len(self.boxes):
                box = self.boxes[self.selected_idx]
                if "bbox" in box:
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

            # Проверка нажатия на точки любого полигона
            tol = 12
            for idx, box in enumerate(self.boxes):
                if "polygon" in box and box["polygon"]:
                    for p_idx, pt in enumerate(box["polygon"]):
                        sx, sy = self.image_to_screen(pt[0], pt[1])
                        if abs(event.x() - sx) < tol and abs(event.y() - sy) < tol:
                            self.save_state_to_history()
                            self.selected_idx = idx
                            self.selection_changed.emit(idx)
                            self.dragging_point_idx = p_idx
                            self.drag_polygon_idx = idx
                            self.update()
                            return

            # Проверка клика внутри полигона или бокса (полигоны приоритетнее)
            from PyQt5.QtGui import QPolygonF
            from PyQt5.QtCore import QPointF
            for idx, box in enumerate(self.boxes):
                if "polygon" in box and box["polygon"]:
                    poly_f = QPolygonF([QPointF(pt[0], pt[1]) for pt in box["polygon"]])
                    if poly_f.containsPoint(QPointF(x, y), Qt.OddEvenFill):
                        self.save_state_to_history()
                        self.dragging_box = True
                        self.drag_box_idx = idx
                        self.drag_start_pos = (x, y)
                        self.original_polygon = list(box["polygon"])
                        self.selected_idx = idx
                        self.selection_changed.emit(idx)
                        self.update()
                        return
                        
            # Если не попали в полигон, проверяем прямоугольники
            for idx, box in enumerate(self.boxes):
                if "bbox" in box and not box.get("polygon"):
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
            if self.draw_mode == 'polygon':
                # Первую точку тоже фиксируем при отпускании; пока показываем призрак
                self.polygon_points = []
                self._poly_ghost_pos = (round(x), round(y))
                self._poly_press_hit_idx = -1
            else:
                self.drag_start = (x, y)
                self.drag_end = (x, y)
            self.update()

    def mouseDoubleClickEvent(self, event):
        """Двойной клик завершает полигон."""
        if self.draw_mode == 'polygon' and self.drawing and len(self.polygon_points) >= 3:
            self.finish_polygon()

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

            if 0 <= self.selected_idx < len(self.boxes):
                self.boxes[self.selected_idx]["bbox"] = [new_x1, new_y1, new_x2, new_y2]
                self.boxes_changed.emit()
                self.update()
            return

        if getattr(self, 'dragging_temp_point_idx', -1) >= 0 and self.drawing and self.draw_mode == 'polygon':
            self.polygon_points[self.dragging_temp_point_idx] = (round(x), round(y))
            self.update()
            return

        # Обновляем «призрачную» точку при зажатой ЛКМ в режиме полигона (новая точка ещё не зафиксирована)
        if self.drawing and self.draw_mode == 'polygon' and self._poly_ghost_pos is not None:
            self._poly_ghost_pos = (round(x), round(y))
            self.update()
            return

        if self.dragging_point_idx >= 0 and self.drag_polygon_idx >= 0:
            poly = self.boxes[self.drag_polygon_idx].get("polygon")
            if poly:
                poly[self.dragging_point_idx] = (round(x), round(y))
                # Update bbox
                xs = [p[0] for p in poly]
                ys = [p[1] for p in poly]
                self.boxes[self.drag_polygon_idx]["bbox"] = [min(xs), min(ys), max(xs), max(ys)]
                self.boxes_changed.emit()
                self.update()
            return

        if self.dragging_box and self.drag_start_pos and self.original_polygon:
            dx = x - self.drag_start_pos[0]
            dy = y - self.drag_start_pos[1]
            h, w, _ = self.image_orig.shape
            new_poly = []
            for pt in self.original_polygon:
                nx = max(0, min(w, round(pt[0] + dx)))
                ny = max(0, min(h, round(pt[1] + dy)))
                new_poly.append((nx, ny))
            if self.drag_box_idx >= 0:
                self.boxes[self.drag_box_idx]["polygon"] = new_poly
                xs = [p[0] for p in new_poly]
                ys = [p[1] for p in new_poly]
                self.boxes[self.drag_box_idx]["bbox"] = [min(xs), min(ys), max(xs), max(ys)]
                self.boxes_changed.emit()
                self.update()
            return
            
        elif self.dragging_box and self.drag_start_pos and self.original_box:
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

        if self.drawing and self.draw_mode == 'box':
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
                self.original_polygon = None
                self.boxes_changed.emit()
                return

            # Режим полигона: фиксируем точку при ОТПУСКАНИИ
            if self.draw_mode == 'polygon' and self.drawing:
                hit_idx = self._poly_press_hit_idx
                self._poly_press_hit_idx = -1
                self.dragging_temp_point_idx = -1
                self._poly_ghost_pos = None

                x, y = self.screen_to_image(event.x(), event.y())
                if x < 0 or y < 0 or x >= self.image_orig.shape[1] or y >= self.image_orig.shape[0]:
                    self.update()
                    return

                if hit_idx == 0 and len(self.polygon_points) >= 3:
                    # Отпустили на первой точке — закрываем полигон
                    self.finish_polygon()
                    return
                elif hit_idx > 0:
                    # Отпустили после перетаскивания существующей точки — ничего не добавляем
                    self.boxes_changed.emit()
                    self.update()
                    return
                else:
                    # Отпустили в пустом месте — добавляем точку
                    self.polygon_points.append((round(x), round(y)))
                    self.update()
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
                        self.status_message.emit(f"{tr('Добавлен бокс класса')} {self.current_class}")
                        self.boxes_changed.emit()
                self.drawing = False
                self.drag_start = None
                self.drag_end = None
                self.update()

        if self.dragging_point_idx >= 0:
            self.dragging_point_idx = -1
            self.drag_polygon_idx = -1
            self.boxes_changed.emit()
            self.update()

    def finish_polygon(self):
        """Завершает рисование полигона и добавляет его в список аннотаций."""
        if len(self.polygon_points) >= 3:
            # Вычисляем bbox из полигона
            xs = [p[0] for p in self.polygon_points]
            ys = [p[1] for p in self.polygon_points]
            bbox = [min(xs), min(ys), max(xs), max(ys)]
            new_box = {
                "bbox": bbox,
                "polygon": list(self.polygon_points),
                "class": self.current_class
            }
            self.boxes.append(new_box)
            self.selected_idx = len(self.boxes) - 1
            self.selection_changed.emit(self.selected_idx)
            n = len(self.polygon_points)
            self.status_message.emit(f"{tr('Добавлен полигон класса')} {self.current_class} ({n} {tr('точек')})")
            self.boxes_changed.emit()
        self.polygon_points = []
        self._poly_ghost_pos = None
        self._poly_press_hit_idx = -1
        self.drawing = False
        self.update()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Delete and 0 <= self.selected_idx < len(self.boxes):
            self.delete_selected()
        elif event.modifiers() & Qt.ControlModifier and event.key() == Qt.Key_Z:
            self.undo()
        elif event.key() == Qt.Key_S:
            self.emit_status(tr("Сохранить (авто)"))
        elif event.key() == Qt.Key_N:
            self.start_drawing()
        elif event.key() == Qt.Key_P:
            self.toggle_polygon_mode()
        elif event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            # Enter завершает полигон
            if self.draw_mode == 'polygon' and self.drawing and len(self.polygon_points) >= 3:
                self.finish_polygon()
        elif event.key() == Qt.Key_Escape:
            # Escape отменяет текущее рисование
            if self.drawing:
                self.drawing = False
                self.polygon_points = []
                self._poly_ghost_pos = None
                self._poly_press_hit_idx = -1
                self.drag_start = None
                self.drag_end = None
                self.update()
        else:
            super().keyPressEvent(event)

    def toggle_polygon_mode(self):
        """Переключает режим рисования между прямоугольником и полигоном."""
        if self.draw_mode == 'box':
            self.draw_mode = 'polygon'
            self.status_message.emit(tr("Режим: Полигон"))
        else:
            self.draw_mode = 'box'
            self.status_message.emit(tr("Режим: Прямоугольник"))

    def start_drawing(self):
        """Принудительно начать рисование бокса (не меняет draw_mode если уже box)."""
        self.draw_mode = 'box'
        self.drawing = True
        self.drag_start = None
        self.drag_end = None
        self.polygon_points = []
        self.status_message.emit(tr("Рисуйте новый бокс"))

    def start_polygon_drawing(self):
        self.draw_mode = 'polygon'
        self.drawing = True
        self.polygon_points = []
        self.status_message.emit(tr("Рисуйте полигон (клик — точка, Enter/двойной клик — завершить)"))

    def delete_selected(self):
        if 0 <= self.selected_idx < len(self.boxes):
            self.save_state_to_history()
            del self.boxes[self.selected_idx]
            self.selected_idx = -1
            self.selection_changed.emit(-1)
            self.boxes_changed.emit()
            self.update()

    def save_state_to_history(self):
        if not self.history_enabled:
            return
        state = copy.deepcopy(self.boxes)
        self.history.append(state)

    def undo(self):
        if not self.history:
            self.status_message.emit(tr("Нечего отменять"))
            return
        prev = self.history.pop()
        self.boxes = copy.deepcopy(prev)
        self.selected_idx = -1
        self.selection_changed.emit(-1)
        self.boxes_changed.emit()
        self.update()

    def emit_status(self, msg):
        self.status_message.emit(msg)

    def auto_annotate(self, conf_threshold=0.25, iou_threshold=0.5, cls_conf=0.5):
        if self.detector is None:
            self.status_message.emit(tr("Детектор не загружен"))
            return
        if self.image_orig is None:
            return
        self.status_message.emit(tr("Авторазметка..."))
        try:
            results = self.detector(self.image_orig, conf=conf_threshold, iou=iou_threshold, verbose=False)[0]
            boxes = results.boxes
            if boxes is None or len(boxes) == 0:
                self.status_message.emit(tr("Ничего не найдено"))
                return
            self.save_state_to_history()
            new_boxes = []
            has_masks = hasattr(results, 'masks') and results.masks is not None and len(results.masks.xy) > 0

            for idx, box in enumerate(boxes):
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                
                # Извлекаем класс из модели детектора
                cls_id = int(box.cls[0].item()) if hasattr(box, 'cls') and len(box.cls) > 0 else 0
                class_name = self.detector.names.get(cls_id, self.current_class) if (hasattr(self.detector, 'names') and self.detector.names) else self.current_class
                
                # Если подключен классификатор — уточняем класс
                if self.classifier is not None:
                    crop = self.image_orig[y1:y2, x1:x2]
                    if crop.size > 0 and crop.shape[0] >= 10 and crop.shape[1] >= 10:
                        cls_results = self.classifier(crop, verbose=False)
                        probs = cls_results[0].probs
                        if probs is not None:
                            top_conf = probs.top1conf.item()
                            top_class_id = probs.top1
                            if top_conf >= cls_conf:
                                class_name = self.classifier.names[top_class_id]

                annot_item = {"bbox": [x1, y1, x2, y2], "class": class_name}
                if has_masks and idx < len(results.masks.xy):
                    poly = results.masks.xy[idx]
                    if len(poly) >= 3:
                        annot_item["polygon"] = [[int(round(p[0])), int(round(p[1]))] for p in poly]

                new_boxes.append(annot_item)

            self.boxes.extend(new_boxes)
            self.boxes_changed.emit()
            self.status_message.emit(f"{tr('Добавлено')} {len(new_boxes)} {tr('боксов')}")
            self.update()
        except Exception as e:
            logging.error(f"Auto-annotation error: {e}", exc_info=True)
            self.status_message.emit(f"{tr('Ошибка авторазметки')}: {e}")