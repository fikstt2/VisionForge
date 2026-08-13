# core/smart_segmenter.py
import numpy as np
import cv2
import logging

logger = logging.getLogger(__name__)


class SmartSegmenter:
    """Умный модуль интерактивной сегментации объектов в 1 клик.
    
    Поддерживает:
    1. Модели FastSAM / YOLO-seg через Ultralytics (при наличии весов).
    2. Детекцию границ на базе нейросети + адаптивный GrabCut / Watershed.
    3. Автоматическое определение масштаба объекта и сглаживание контуров.
    """

    def __init__(self, model=None, model_path=None):
        self.model = model
        self.model_path = model_path
        if model_path and model is None:
            self.load_model(model_path)

    def load_model(self, model_path):
        """Загрузка модели сегментации (FastSAM или YOLO-seg)."""
        try:
            from ultralytics import FastSAM, YOLO
            if "fastsam" in model_path.lower():
                self.model = FastSAM(model_path)
            else:
                self.model = YOLO(model_path)
            self.model_path = model_path
            return True, "Модель успешно загружена"
        except Exception as e:
            logger.error(f"Ошибка загрузки модели сегментации {model_path}: {e}")
            self.model = None
            return False, str(e)

    def segment_point(self, img_rgb: np.ndarray, px: int, py: int) -> list:
        """Сегментация объекта по точке клика (px, py).
        
        Возвращает список координат вершин полигона [[x1, y1], [x2, y2], ...].
        """
        if img_rgb is None or img_rgb.size == 0:
            return []

        h, w = img_rgb.shape[:2]
        px = max(0, min(w - 1, int(px)))
        py = max(0, min(h - 1, int(py)))

        # 1. Если загружена нейросетевая модель (YOLO-seg / FastSAM / YOLO-detect)
        if self.model is not None:
            try:
                results = self.model(img_rgb, verbose=False)
                if results and len(results) > 0:
                    res = results[0]
                    
                    # 1.1 Если модель выдает маски сегментации (YOLO-seg / FastSAM)
                    if hasattr(res, 'masks') and res.masks is not None and len(res.masks.xy) > 0:
                        for mask_poly in res.masks.xy:
                            if len(mask_poly) >= 3:
                                poly_np = np.array(mask_poly, dtype=np.int32)
                                dist = cv2.pointPolygonTest(poly_np, (float(px), float(py)), False)
                                if dist >= 0:
                                    return self._simplify_polygon(mask_poly.tolist())

                    # 1.2 Если модель вернула боксы (YOLO-detect) — берем бокс под кликом для точной сегментации
                    if hasattr(res, 'boxes') and res.boxes is not None and len(res.boxes) > 0:
                        for b in res.boxes:
                            bx1, by1, bx2, by2 = map(int, b.xyxy[0])
                            if bx1 <= px <= bx2 and by1 <= py <= by2:
                                poly = self.segment_box(img_rgb, bx1, by1, bx2, by2)
                                if poly and len(poly) >= 3:
                                    return poly
            except Exception as e:
                logger.warning(f"Ошибка инференса модели сегментации: {e}")

        # 2. Адаптивный гибридный алгоритм (FloodFill + GrabCut)
        return self._segment_point_adaptive_grabcut(img_rgb, px, py)

    def segment_box(self, img_rgb: np.ndarray, x1: int, y1: int, x2: int, y2: int) -> list:
        """Сегментация объекта внутри ограничивающего прямоугольника."""
        if img_rgb is None or img_rgb.size == 0:
            return []

        h, w = img_rgb.shape[:2]
        x1, x2 = max(0, min(w - 1, int(min(x1, x2)))), max(0, min(w - 1, int(max(x1, x2))))
        y1, y2 = max(0, min(h - 1, int(min(y1, y2)))), max(0, min(h - 1, int(max(y1, y2))))

        bw = x2 - x1
        bh = y2 - y1
        if bw < 5 or bh < 5:
            return []

        # Запускаем GrabCut с боксом
        margin = 10
        rx1 = max(0, x1 - margin)
        ry1 = max(0, y1 - margin)
        rx2 = min(w, x2 + margin)
        ry2 = min(h, y2 + margin)

        roi = img_rgb[ry1:ry2, rx1:rx2]
        roi_h, roi_w = roi.shape[:2]

        rect = (x1 - rx1, y1 - ry1, bw, bh)
        mask = np.zeros((roi_h, roi_w), np.uint8)
        bgd_model = np.zeros((1, 65), np.float64)
        fgd_model = np.zeros((1, 65), np.float64)

        try:
            cv2.grabCut(roi, mask, rect, bgd_model, fgd_model, 3, cv2.GC_INIT_WITH_RECT)
            binary_mask = np.where((mask == 1) | (mask == 3), 255, 0).astype('uint8')
            poly = self._extract_largest_polygon(binary_mask)
            if poly:
                # Переводим локальные координаты ROI в глобальные координаты изображения
                return [[p[0] + rx1, p[1] + ry1] for p in poly]
        except Exception as e:
            logger.error(f"Ошибка segment_box: {e}")

        return [[x1, y1], [x2, y1], [x2, y2], [x1, y2]]

    def _segment_point_adaptive_grabcut(self, img_rgb: np.ndarray, px: int, py: int) -> list:
        """Адаптивная сегментация крупного или мелкого объекта по точке клика."""
        h, w = img_rgb.shape[:2]

        # Адаптивный размер окрестности (до 50% размера кадра для захвата всего объекта целиком)
        radius = max(180, int(min(h, w) * 0.48))
        x1 = max(0, px - radius)
        y1 = max(0, py - radius)
        x2 = min(w, px + radius)
        y2 = min(h, py + radius)

        roi = img_rgb[y1:y2, x1:x2]
        roi_h, roi_w = roi.shape[:2]
        if roi_h < 15 or roi_w < 15:
            return []

        local_px = px - x1
        local_py = py - y1

        # 1. Начальная грубая сегментация через FloodFill для выделения формы объекта
        flood_mask = np.zeros((roi_h + 2, roi_w + 2), np.uint8)
        roi_bgr = cv2.cvtColor(roi, cv2.COLOR_RGB2BGR)
        
        # Заливка с цветовым допуском от точки клика
        diff = (28, 28, 28)
        flags = 4 | (255 << 8) | cv2.FLOODFILL_MASK_ONLY
        cv2.floodFill(roi_bgr, flood_mask, (local_px, local_py), 0, diff, diff, flags)
        seed_region = flood_mask[1:-1, 1:-1]

        # 2. Инициализация маски GrabCut
        mask = np.full((roi_h, roi_w), cv2.GC_PR_BGD, dtype=np.uint8)
        # Область заливки помечаем как вероятный передний план
        mask[seed_region == 255] = cv2.GC_PR_FGD
        # Непосредственную окрестность клика (ядро объекта) — как точный передний план
        cv2.circle(mask, (local_px, local_py), max(8, int(min(roi_h, roi_w) * 0.08)), cv2.GC_FGD, -1)

        # Внешние границы ROI помечаем как фон
        mask[0:3, :] = cv2.GC_BGD
        mask[-3:, :] = cv2.GC_BGD
        mask[:, 0:3] = cv2.GC_BGD
        mask[:, -3:] = cv2.GC_BGD

        bgd_model = np.zeros((1, 65), np.float64)
        fgd_model = np.zeros((1, 65), np.float64)

        try:
            cv2.grabCut(roi, mask, None, bgd_model, fgd_model, 3, cv2.GC_INIT_WITH_MASK)
            bin_mask = np.where((mask == 1) | (mask == 3), 255, 0).astype('uint8')

            # Морфологическое сглаживание
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
            bin_mask = cv2.morphologyEx(bin_mask, cv2.MORPH_CLOSE, kernel)
            bin_mask = cv2.morphologyEx(bin_mask, cv2.MORPH_OPEN, kernel)

            # Поиск контуров
            contours, _ = cv2.findContours(bin_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if not contours:
                return []

            # Находим контур, содержащий точку клика, или самый крупный рядом
            best_cnt = None
            for cnt in contours:
                if cv2.contourArea(cnt) < 50:
                    continue
                if cv2.pointPolygonTest(cnt, (float(local_px), float(local_py)), False) >= 0:
                    best_cnt = cnt
                    break

            if best_cnt is None:
                # Берем максимальный по площади контур
                best_cnt = max(contours, key=cv2.contourArea)

            if best_cnt is None or len(best_cnt) < 3:
                return []

            poly_local = self._simplify_polygon(best_cnt.reshape(-1, 2).tolist(), tolerance_ratio=0.008)
            # Переводим в глобальные координаты
            return [[int(p[0] + x1), int(p[1] + y1)] for p in poly_local]
        except Exception as e:
            logger.error(f"Ошибка _segment_point_adaptive_grabcut: {e}")
            return []

    def _extract_largest_polygon(self, binary_mask: np.ndarray) -> list:
        """Извлечение сглаженного полигона самого крупного контура из бинарной маски."""
        contours, _ = cv2.findContours(binary_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return []
        largest = max(contours, key=cv2.contourArea)
        if len(largest) < 3:
            return []
        return self._simplify_polygon(largest.reshape(-1, 2).tolist())

    def _simplify_polygon(self, polygon: list, tolerance_ratio: float = 0.006) -> list:
        """Сглаживание и оптимизация количества вершин полигона (алгоритм Рамера-Дугласа-Пекера)."""
        if not polygon or len(polygon) < 3:
            return polygon

        pts = np.array(polygon, dtype=np.int32).reshape((-1, 1, 2))
        perimeter = cv2.arcLength(pts, True)
        epsilon = max(1.5, tolerance_ratio * perimeter)
        approx = cv2.approxPolyDP(pts, epsilon, True)

        simplified = approx.reshape(-1, 2).tolist()
        return simplified if len(simplified) >= 3 else polygon
