# core/dataset_deduplicator.py
import os
import cv2
import numpy as np
import logging

logger = logging.getLogger(__name__)


class DatasetDeduplicator:
    """Модуль поиска дубликатов, похожих серийных кадров и оценки качества изображений."""

    @classmethod
    def compute_phash(cls, img_rgb: np.ndarray, hash_size: int = 8) -> np.ndarray:
        """Вычисление 64-битного перцептивного хеша (pHash) на основе 2D DCT."""
        if img_rgb is None or img_rgb.size == 0:
            return np.zeros(hash_size * hash_size, dtype=bool)

        gray = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)
        # Ресайз до 32x32 для выделения низкочастотных признаков
        resized = cv2.resize(gray, (32, 32), interpolation=cv2.INTER_AREA)
        float_img = np.float32(resized)

        # 2D Дискретное косинусное преобразование
        dct = cv2.dct(float_img)
        # Берем левый верхний квадрат частот 8x8 (исключая DC составляющую (0,0))
        dct_low = dct[:hash_size, :hash_size]
        med = np.median(dct_low)
        return (dct_low > med).flatten()

    @classmethod
    def hamming_distance(cls, hash1: np.ndarray, hash2: np.ndarray) -> int:
        """Вычисление расстояния Хэмминга между двумя хешами."""
        return int(np.count_nonzero(hash1 != hash2))

    @classmethod
    def similarity_pct(cls, hash1: np.ndarray, hash2: np.ndarray) -> float:
        """Процент схожести от 0.0% до 100.0%."""
        dist = cls.hamming_distance(hash1, hash2)
        total_bits = len(hash1)
        return round(max(0.0, (1.0 - (dist / total_bits))) * 100.0, 1)

    @classmethod
    def analyze_dataset(
        cls,
        images_dir: str,
        image_list: list,
        similarity_threshold: float = 90.0,
        blur_threshold: float = 60.0,
        progress_callback = None
    ) -> dict:
        """Комплексный анализ датасета: поиск групп дубликатов и мусорных кадров.
        
        Возвращает:
        {
            "duplicate_groups": [
                {
                    "primary": "frame_001.jpg",
                    "duplicates": [
                        {"file": "frame_002.jpg", "similarity": 98.4, "distance": 1}
                    ]
                }
            ],
            "low_quality": [
                {"file": "dark_frame.jpg", "reason": "Слишком темный (яркость 5.2)", "score": 5.2}
            ],
            "total_scanned": N
        }
        """
        hashes = {}
        qualities = []
        total = len(image_list)

        # 1. Вычисляем хеши и метрики качества
        for idx, filename in enumerate(image_list):
            full_path = os.path.join(images_dir, filename)
            if not os.path.exists(full_path):
                continue

            img_bgr = cv2.imread(full_path)
            if img_bgr is None:
                qualities.append({
                    "file": filename,
                    "reason": "Поврежденный файл (не удалось прочесть)",
                    "score": 0.0
                })
                continue

            img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
            gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

            # Оценка размытости (Лапласиан)
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            mean_val = float(np.mean(gray))

            if mean_val < 10.0:
                qualities.append({
                    "file": filename,
                    "reason": f"Слишком тёмный кадр (яркость {mean_val:.1f})",
                    "score": mean_val
                })
            elif mean_val > 245.0:
                qualities.append({
                    "file": filename,
                    "reason": f"Пересвеченный / белый кадр (яркость {mean_val:.1f})",
                    "score": mean_val
                })
            elif laplacian_var < blur_threshold:
                qualities.append({
                    "file": filename,
                    "reason": f"Сильное размытие (резкость {laplacian_var:.1f})",
                    "score": laplacian_var
                })

            hashes[filename] = cls.compute_phash(img_rgb)

            if progress_callback and idx % 10 == 0:
                progress_callback(int((idx / max(1, total)) * 50))

        # 2. Поиск пар и кластеризация дубликатов
        filenames = list(hashes.keys())
        visited = set()
        duplicate_groups = []

        max_dist = int((1.0 - (similarity_threshold / 100.0)) * 64)

        for i in range(len(filenames)):
            f_i = filenames[i]
            if f_i in visited:
                continue

            h_i = hashes[f_i]
            group_dupes = []

            for j in range(i + 1, len(filenames)):
                f_j = filenames[j]
                if f_j in visited:
                    continue

                h_j = hashes[f_j]
                dist = cls.hamming_distance(h_i, h_j)

                if dist <= max_dist:
                    sim = cls.similarity_pct(h_i, h_j)
                    group_dupes.append({
                        "file": f_j,
                        "similarity": sim,
                        "distance": dist
                    })
                    visited.add(f_j)

            if group_dupes:
                visited.add(f_i)
                duplicate_groups.append({
                    "primary": f_i,
                    "duplicates": group_dupes
                })

            if progress_callback and i % 10 == 0:
                progress_callback(50 + int((i / max(1, len(filenames))) * 50))

        if progress_callback:
            progress_callback(100)

        return {
            "duplicate_groups": duplicate_groups,
            "low_quality": qualities,
            "total_scanned": total
        }
