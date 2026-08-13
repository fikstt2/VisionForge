# core/track_interpolator.py
import numpy as np
import copy
import logging

logger = logging.getLogger(__name__)


class TrackInterpolator:
    """Модуль интерполяции траекторий боксов и полигонов между ключевыми кадрами."""

    @staticmethod
    def interpolate_bbox(bbox_a: list, bbox_b: list, t: float) -> list:
        """Линейная интерполяция между двумя ограничивающими прямоугольниками.
        
        t: коэффициент прогресса от 0.0 (bbox_a) до 1.0 (bbox_b).
        """
        x1 = round(bbox_a[0] + (bbox_b[0] - bbox_a[0]) * t)
        y1 = round(bbox_a[1] + (bbox_b[1] - bbox_a[1]) * t)
        x2 = round(bbox_a[2] + (bbox_b[2] - bbox_a[2]) * t)
        y2 = round(bbox_a[3] + (bbox_b[3] - bbox_a[3]) * t)
        return [int(x1), int(y1), int(x2), int(y2)]

    @staticmethod
    def resample_polygon(polygon: list, target_count: int) -> list:
        """Ресэмплинг полигона вдоль периметра до точного числа вершин target_count."""
        if not polygon:
            return []
        if len(polygon) == target_count:
            return [[int(p[0]), int(p[1])] for p in polygon]

        pts = np.array(polygon, dtype=np.float32)
        # Замыкаем контур для расчета расстояний
        pts_closed = np.vstack([pts, pts[0]])
        diffs = np.diff(pts_closed, axis=0)
        segment_lengths = np.sqrt((diffs ** 2).sum(axis=1))
        perimeter = segment_lengths.sum()

        if perimeter == 0:
            return [[int(pts[0][0]), int(pts[0][1])]] * target_count

        cumulative_lengths = np.concatenate([[0.0], np.cumsum(segment_lengths)])
        sample_distances = np.linspace(0, perimeter, target_count, endpoint=False)

        resampled = []
        for d in sample_distances:
            idx = np.searchsorted(cumulative_lengths, d) - 1
            idx = max(0, min(len(segment_lengths) - 1, idx))
            seg_len = segment_lengths[idx]
            if seg_len > 0:
                frac = (d - cumulative_lengths[idx]) / seg_len
                pt = pts_closed[idx] + diffs[idx] * frac
            else:
                pt = pts_closed[idx]
            resampled.append([int(round(pt[0])), int(round(pt[1]))])

        return resampled

    @classmethod
    def interpolate_polygon(cls, poly_a: list, poly_b: list, t: float) -> list:
        """Интерполяция вершин между двумя полигонами."""
        if not poly_a or not poly_b:
            return copy.deepcopy(poly_a if t < 0.5 else poly_b)

        target_n = max(len(poly_a), len(poly_b), 4)
        r_a = cls.resample_polygon(poly_a, target_n)
        r_b = cls.resample_polygon(poly_b, target_n)

        # Выравнивание циклического сдвига для минимизации расстояний
        best_shift = 0
        min_dist_sum = float('inf')
        pts_a_np = np.array(r_a)
        pts_b_np = np.array(r_b)

        for shift in range(target_n):
            shifted_b = np.roll(pts_b_np, shift, axis=0)
            dists = np.sum((pts_a_np - shifted_b) ** 2)
            if dists < min_dist_sum:
                min_dist_sum = dists
                best_shift = shift

        pts_b_aligned = np.roll(pts_b_np, best_shift, axis=0)

        interpolated = []
        for i in range(target_n):
            ix = round(pts_a_np[i][0] + (pts_b_aligned[i][0] - pts_a_np[i][0]) * t)
            iy = round(pts_a_np[i][1] + (pts_b_aligned[i][1] - pts_a_np[i][1]) * t)
            interpolated.append([int(ix), int(iy)])

        return interpolated

    @classmethod
    def interpolate_object_lists(cls, boxes_start: list, boxes_end: list, num_steps: int) -> list:
        """Интерполяция списков объектов между двумя кадрами на num_steps промежуточных кадров.
        
        Возвращает список длины num_steps, где каждый элемент — список аннотаций кадра.
        """
        results = [[] for _ in range(num_steps)]
        if num_steps <= 0:
            return results

        # Сопоставляем объекты по классам и расстояниям
        matched_pairs = []
        unmatched_end = list(range(len(boxes_end)))

        for i, b_start in enumerate(boxes_start):
            cls_start = b_start.get("class", "unknown")
            best_j = -1
            best_iou = -1.0

            for j in unmatched_end:
                b_end = boxes_end[j]
                if b_end.get("class") == cls_start:
                    iou = cls._calculate_iou(b_start.get("bbox", [0, 0, 0, 0]), b_end.get("bbox", [0, 0, 0, 0]))
                    if iou > best_iou:
                        best_iou = iou
                        best_j = j

            if best_j != -1:
                matched_pairs.append((i, best_j))
                unmatched_end.remove(best_j)
            elif len(boxes_end) == 1 and len(boxes_start) == 1:
                # Если по 1 объекту на кадре — матчим даже если класс отличается
                matched_pairs.append((0, 0))

        # Выполняем интерполяцию для всех промежуточных шагов
        for step_idx in range(num_steps):
            t = (step_idx + 1) / (num_steps + 1)
            frame_boxes = []

            for start_idx, end_idx in matched_pairs:
                obj_a = boxes_start[start_idx]
                obj_b = boxes_end[end_idx]
                cls_name = obj_a.get("class") or obj_b.get("class", "unknown")

                has_poly_a = "polygon" in obj_a and obj_a["polygon"]
                has_poly_b = "polygon" in obj_b and obj_b["polygon"]

                interpolated_obj = {"class": cls_name}

                if has_poly_a and has_poly_b:
                    inter_poly = cls.interpolate_polygon(obj_a["polygon"], obj_b["polygon"], t)
                    xs = [p[0] for p in inter_poly]
                    ys = [p[1] for p in inter_poly]
                    inter_bbox = [min(xs), min(ys), max(xs), max(ys)]
                    interpolated_obj["polygon"] = inter_poly
                    interpolated_obj["bbox"] = inter_bbox
                elif "bbox" in obj_a and "bbox" in obj_b:
                    inter_bbox = cls.interpolate_bbox(obj_a["bbox"], obj_b["bbox"], t)
                    interpolated_obj["bbox"] = inter_bbox
                    if has_poly_a:
                        interpolated_obj["polygon"] = copy.deepcopy(obj_a["polygon"])
                    elif has_poly_b:
                        interpolated_obj["polygon"] = copy.deepcopy(obj_b["polygon"])

                frame_boxes.append(interpolated_obj)

            results[step_idx] = frame_boxes

        return results

    @classmethod
    def interpolate_project_sequence(cls, project, start_image: str, end_image: str, mode: str = "main") -> int:
        """Интерполяция последовательности кадров в проекте между start_image и end_image.
        
        Возвращает количество обновленных промежуточных кадров.
        """
        if start_image not in project.images_list or end_image not in project.images_list:
            raise ValueError(f"Изображения {start_image} или {end_image} не найдены в списке проекта.")

        idx_start = project.images_list.index(start_image)
        idx_end = project.images_list.index(end_image)

        if idx_start > idx_end:
            idx_start, idx_end = idx_end, idx_start
            start_image, end_image = end_image, start_image

        intermediate_names = project.images_list[idx_start + 1 : idx_end]
        num_intermediate = len(intermediate_names)
        if num_intermediate == 0:
            return 0

        boxes_start = project.get_annotations(start_image, mode=mode)
        boxes_end = project.get_annotations(end_image, mode=mode)

        interpolated_frames = cls.interpolate_object_lists(boxes_start, boxes_end, num_intermediate)

        for img_name, frame_boxes in zip(intermediate_names, interpolated_frames):
            project.set_annotations(img_name, frame_boxes, mode=mode)

        project.save()
        return num_intermediate

    @staticmethod
    def _calculate_iou(box_a: list, box_b: list) -> float:
        """Вычисление Intersection over Union (IoU) между двумя боксами."""
        xA = max(box_a[0], box_b[0])
        yA = max(box_a[1], box_b[1])
        xB = min(box_a[2], box_b[2])
        yB = min(box_a[3], box_b[3])

        inter_area = max(0, xB - xA) * max(0, yB - yA)
        box_a_area = max(0, box_a[2] - box_a[0]) * max(0, box_a[3] - box_a[1])
        box_b_area = max(0, box_b[2] - box_b[0]) * max(0, box_b[3] - box_b[1])

        union_area = float(box_a_area + box_b_area - inter_area)
        if union_area <= 0:
            return 0.0
        return inter_area / union_area
