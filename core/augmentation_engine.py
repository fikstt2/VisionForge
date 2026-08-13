# core/augmentation_engine.py
import cv2
import numpy as np
import copy
import logging

logger = logging.getLogger(__name__)


class AugmentationEngine:
    """Движок интерактивной аугментации изображений и геометрического пересчета аннотаций."""

    @classmethod
    def apply_transformations(cls, img_rgb: np.ndarray, boxes: list, params: dict) -> tuple:
        """Применяет параметры аугментации к изображению и пересчитывает боксы и полигоны.
        
        params:
            - flip_h: bool
            - flip_v: bool
            - rotation: float (в градусах, e.g. -45..45)
            - scale: float (0.5..2.0)
            - shift_x: float (-0.2..0.2 от ширины)
            - shift_y: float (-0.2..0.2 от высоты)
            - hsv_h: float (-0.5..0.5)
            - hsv_s: float (0.0..2.0)
            - hsv_v: float (0.0..2.0)
            - blur: int (0, 3, 5, 7, 9)
            - noise: float (0..50)
            - weather: str ('none', 'rain', 'fog')
            - cutout_count: int (0..5)
        
        Возвращает: (aug_img_rgb, aug_boxes)
        """
        if img_rgb is None or img_rgb.size == 0:
            return img_rgb, boxes

        h, w = img_rgb.shape[:2]
        aug_img = img_rgb.copy()
        aug_boxes = copy.deepcopy(boxes)

        # 1. Горизонтальное и вертикальное отражение (Flip)
        flip_h = params.get("flip_h", False)
        flip_v = params.get("flip_v", False)

        if flip_h:
            aug_img = cv2.flip(aug_img, 1)
            for b in aug_boxes:
                if "bbox" in b and b["bbox"]:
                    x1, y1, x2, y2 = b["bbox"]
                    b["bbox"] = [w - x2, y1, w - x1, y2]
                if "polygon" in b and b["polygon"]:
                    b["polygon"] = [[w - pt[0], pt[1]] for pt in b["polygon"]]

        if flip_v:
            aug_img = cv2.flip(aug_img, 0)
            for b in aug_boxes:
                if "bbox" in b and b["bbox"]:
                    x1, y1, x2, y2 = b["bbox"]
                    b["bbox"] = [x1, h - y2, x2, h - y1]
                if "polygon" in b and b["polygon"]:
                    b["polygon"] = [[pt[0], h - pt[1]] for pt in b["polygon"]]

        # 2. Аффинные трансформации: Поворот, Масштаб, Сдвиг
        rot = params.get("rotation", 0.0)
        scale = params.get("scale", 1.0)
        shift_x = params.get("shift_x", 0.0) * w
        shift_y = params.get("shift_y", 0.0) * h

        if rot != 0.0 or scale != 1.0 or shift_x != 0.0 or shift_y != 0.0:
            center = (w / 2.0, h / 2.0)
            M = cv2.getRotationMatrix2D(center, rot, scale)
            M[0, 2] += shift_x
            M[1, 2] += shift_y

            aug_img = cv2.warpAffine(aug_img, M, (w, h), borderMode=cv2.BORDER_REFLECT_101)

            # Трансформация координат аннотаций
            new_boxes = []
            for b in aug_boxes:
                transformed_obj = {"class": b.get("class", "unknown")}

                if "polygon" in b and b["polygon"]:
                    pts = np.array(b["polygon"], dtype=np.float32)
                    pts_homo = np.hstack([pts, np.ones((len(pts), 1), dtype=np.float32)])
                    trans_pts = pts_homo.dot(M.T)

                    # Ограничиваем в пределах кадра
                    clipped_poly = []
                    for p in trans_pts:
                        cx = int(max(0, min(w - 1, round(p[0]))))
                        cy = int(max(0, min(h - 1, round(p[1]))))
                        clipped_poly.append([cx, cy])

                    if len(clipped_poly) >= 3:
                        xs = [p[0] for p in clipped_poly]
                        ys = [p[1] for p in clipped_poly]
                        if (max(xs) - min(xs)) >= 3 and (max(ys) - min(ys)) >= 3:
                            transformed_obj["polygon"] = clipped_poly
                            transformed_obj["bbox"] = [min(xs), min(ys), max(xs), max(ys)]
                            new_boxes.append(transformed_obj)
                            continue

                if "bbox" in b and b["bbox"]:
                    x1, y1, x2, y2 = b["bbox"]
                    corners = np.array([
                        [x1, y1, 1],
                        [x2, y1, 1],
                        [x2, y2, 1],
                        [x1, y2, 1]
                    ], dtype=np.float32)
                    trans_corners = corners.dot(M.T)
                    nx1 = int(max(0, min(w - 1, round(trans_corners[:, 0].min()))))
                    nx2 = int(max(0, min(w - 1, round(trans_corners[:, 0].max()))))
                    ny1 = int(max(0, min(h - 1, round(trans_corners[:, 1].min()))))
                    ny2 = int(max(0, min(h - 1, round(trans_corners[:, 1].max()))))

                    if (nx2 - nx1) >= 4 and (ny2 - ny1) >= 4:
                        transformed_obj["bbox"] = [nx1, ny1, nx2, ny2]
                        new_boxes.append(transformed_obj)

            aug_boxes = new_boxes

        # 3. Фотометрические трансформации (HSV)
        hsv_h = params.get("hsv_h", 0.0)
        hsv_s = params.get("hsv_s", 1.0)
        hsv_v = params.get("hsv_v", 1.0)

        if hsv_h != 0.0 or hsv_s != 1.0 or hsv_v != 1.0:
            hsv = cv2.cvtColor(aug_img, cv2.COLOR_RGB2HSV).astype(np.float32)
            hsv[:, :, 0] = (hsv[:, :, 0] + hsv_h * 180) % 180
            hsv[:, :, 1] = np.clip(hsv[:, :, 1] * hsv_s, 0, 255)
            hsv[:, :, 2] = np.clip(hsv[:, :, 2] * hsv_v, 0, 255)
            aug_img = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2RGB)

        # 4. Размытие (Blur)
        blur_k = params.get("blur", 0)
        if blur_k > 1:
            if blur_k % 2 == 0:
                blur_k += 1
            aug_img = cv2.GaussianBlur(aug_img, (blur_k, blur_k), 0)

        # 5. Шум (Gaussian Noise)
        noise_std = params.get("noise", 0.0)
        if noise_std > 0:
            noise = np.random.normal(0, noise_std, aug_img.shape).astype(np.float32)
            aug_img = np.clip(aug_img.astype(np.float32) + noise, 0, 255).astype(np.uint8)

        # 6. Погодные эффекты: Дождь / Туман
        weather = params.get("weather", "none")
        if weather == "rain":
            aug_img = cls._apply_rain(aug_img)
        elif weather == "fog":
            aug_img = cls._apply_fog(aug_img)

        # 7. Cutout
        cutout_count = params.get("cutout_count", 0)
        if cutout_count > 0:
            for _ in range(cutout_count):
                cut_w = np.random.randint(int(w * 0.05), max(int(w * 0.05) + 1, int(w * 0.20)))
                cut_h = np.random.randint(int(h * 0.05), max(int(h * 0.05) + 1, int(h * 0.20)))
                cx = np.random.randint(0, max(1, w - cut_w))
                cy = np.random.randint(0, max(1, h - cut_h))
                aug_img[cy : cy + cut_h, cx : cx + cut_w] = np.random.randint(0, 128, 3, dtype=np.uint8)

        return aug_img, aug_boxes

    @staticmethod
    def _apply_rain(img: np.ndarray) -> np.ndarray:
        """Синтетический эффект дождя."""
        h, w = img.shape[:2]
        rain_layer = np.zeros((h, w), dtype=np.uint8)
        num_drops = int(w * h * 0.001)
        for _ in range(num_drops):
            x = np.random.randint(0, w)
            y = np.random.randint(0, h)
            length = np.random.randint(10, 25)
            angle_dx = np.random.randint(-3, 3)
            cv2.line(rain_layer, (x, y), (x + angle_dx, min(h - 1, y + length)), 200, 1)
        rain_layer = cv2.blur(rain_layer, (3, 3))
        res = img.astype(np.float32)
        res[:, :, 0] += rain_layer * 0.5
        res[:, :, 1] += rain_layer * 0.5
        res[:, :, 2] += rain_layer * 0.6
        return np.clip(res, 0, 255).astype(np.uint8)

    @staticmethod
    def _apply_fog(img: np.ndarray) -> np.ndarray:
        """Синтетический эффект тумана / дымки."""
        h, w = img.shape[:2]
        fog_val = 180
        alpha = 0.35
        fog_layer = np.full((h, w, 3), fog_val, dtype=np.uint8)
        return cv2.addWeighted(img, 1.0 - alpha, fog_layer, alpha, 0)
