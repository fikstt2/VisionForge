# tests/test_smart_segmenter.py
import unittest
import numpy as np
import cv2
from core.smart_segmenter import SmartSegmenter


class TestSmartSegmenter(unittest.TestCase):
    def setUp(self):
        self.segmenter = SmartSegmenter()

        # Создаем тестовое синтетическое изображение с ярким кругом по центру
        self.test_img = np.zeros((200, 200, 3), dtype=np.uint8)
        self.test_img[:] = (30, 30, 30)  # тёмно-серый фон
        cv2.circle(self.test_img, (100, 100), 40, (220, 50, 50), -1)  # яркий объект

    def test_segment_point_valid(self):
        """Проверка клика по объекту в центре."""
        poly = self.segmenter.segment_point(self.test_img, 100, 100)
        self.assertIsInstance(poly, list)
        self.assertGreaterEqual(len(poly), 3, "Полигон должен содержать минимум 3 вершины")
        # Проверяем, что координаты внутри границ изображения
        for pt in poly:
            self.assertGreaterEqual(pt[0], 0)
            self.assertLess(pt[0], 200)
            self.assertGreaterEqual(pt[1], 0)
            self.assertLess(pt[1], 200)

    def test_segment_point_empty_image(self):
        """Проверка защиты от пустого или некорректного изображения."""
        poly = self.segmenter.segment_point(None, 50, 50)
        self.assertEqual(poly, [])

        empty_np = np.zeros((0, 0, 3), dtype=np.uint8)
        poly2 = self.segmenter.segment_point(empty_np, 50, 50)
        self.assertEqual(poly2, [])

    def test_segment_box(self):
        """Проверка сегментации внутри ограничивающего бокса."""
        poly = self.segmenter.segment_box(self.test_img, 50, 50, 150, 150)
        self.assertIsInstance(poly, list)
        self.assertGreaterEqual(len(poly), 3)

    def test_simplify_polygon(self):
        """Проверка упрощения полигона с большим количеством точек."""
        # 100 точек на окружности
        circle_pts = []
        for angle in np.linspace(0, 2 * np.pi, 100, endpoint=False):
            circle_pts.append([int(100 + 40 * np.cos(angle)), int(100 + 40 * np.sin(angle))])

        simplified = self.segmenter._simplify_polygon(circle_pts, tolerance_ratio=0.01)
        self.assertLess(len(simplified), len(circle_pts))
        self.assertGreaterEqual(len(simplified), 3)


if __name__ == "__main__":
    unittest.main()
