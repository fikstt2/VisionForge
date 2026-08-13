# tests/test_dataset_deduplicator.py
import unittest
import os
import shutil
import tempfile
import cv2
import numpy as np
from core.dataset_deduplicator import DatasetDeduplicator


class TestDatasetDeduplicator(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

        # Создаем 3 картинки: 2 идентичные (дубликаты), 1 затемненную
        self.img1_path = os.path.join(self.temp_dir, "img1.jpg")
        self.img2_path = os.path.join(self.temp_dir, "img2.jpg")
        self.img_dark_path = os.path.join(self.temp_dir, "img_dark.jpg")

        sample = np.full((120, 120, 3), 128, dtype=np.uint8)
        cv2.circle(sample, (60, 60), 30, (255, 0, 0), -1)

        cv2.imwrite(self.img1_path, sample)
        cv2.imwrite(self.img2_path, sample)  # полный дубликат

        dark_sample = np.zeros((120, 120, 3), dtype=np.uint8)
        cv2.imwrite(self.img_dark_path, dark_sample)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_phash_exact_match(self):
        """Проверка нулевого расстояния Хэмминга для идентичных изображений."""
        img = cv2.imread(self.img1_path)
        h1 = DatasetDeduplicator.compute_phash(img)
        h2 = DatasetDeduplicator.compute_phash(img)
        dist = DatasetDeduplicator.hamming_distance(h1, h2)
        sim = DatasetDeduplicator.similarity_pct(h1, h2)

        self.assertEqual(dist, 0)
        self.assertEqual(sim, 100.0)

    def test_analyze_dataset(self):
        """Проверка комплексного анализа: обнаружение дубликатов и мусорного кадра."""
        image_list = ["img1.jpg", "img2.jpg", "img_dark.jpg"]
        results = DatasetDeduplicator.analyze_dataset(
            images_dir=self.temp_dir,
            image_list=image_list,
            similarity_threshold=95.0
        )

        # 1. Проверяем дубликаты
        dupes = results["duplicate_groups"]
        self.assertEqual(len(dupes), 1)
        self.assertEqual(dupes[0]["primary"], "img1.jpg")
        self.assertEqual(dupes[0]["duplicates"][0]["file"], "img2.jpg")
        self.assertEqual(dupes[0]["duplicates"][0]["similarity"], 100.0)

        # 2. Проверяем мусорный/темный кадр
        low_q = results["low_quality"]
        flagged_files = [item["file"] for item in low_q]
        self.assertIn("img_dark.jpg", flagged_files)


if __name__ == "__main__":
    unittest.main()
