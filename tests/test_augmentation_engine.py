# tests/test_augmentation_engine.py
import unittest
import numpy as np
from core.augmentation_engine import AugmentationEngine


class TestAugmentationEngine(unittest.TestCase):
    def setUp(self):
        # Синтетическое изображение 100x100 RGB
        self.test_img = np.zeros((100, 100, 3), dtype=np.uint8)
        self.test_boxes = [
            {
                "bbox": [10, 10, 40, 40],
                "polygon": [[10, 10], [40, 10], [40, 40], [10, 40]],
                "class": "person"
            }
        ]

    def test_flip_horizontal(self):
        """Проверка горизонтального отражения координат."""
        params = {"flip_h": True}
        aug_img, aug_boxes = AugmentationEngine.apply_transformations(
            self.test_img, self.test_boxes, params
        )
        self.assertEqual(aug_img.shape, self.test_img.shape)
        # Исходный x1=10, x2=40 при w=100 -> новые координаты x1 = 100-40 = 60, x2 = 100-10 = 90
        new_bbox = aug_boxes[0]["bbox"]
        self.assertEqual(new_bbox, [60, 10, 90, 40])

    def test_flip_vertical(self):
        """Проверка вертикального отражения координат."""
        params = {"flip_v": True}
        aug_img, aug_boxes = AugmentationEngine.apply_transformations(
            self.test_img, self.test_boxes, params
        )
        # Исходный y1=10, y2=40 при h=100 -> новые y1 = 100-40 = 60, y2 = 100-10 = 90
        new_bbox = aug_boxes[0]["bbox"]
        self.assertEqual(new_bbox, [10, 60, 40, 90])

    def test_color_and_blur(self):
        """Проверка фотометрических фильтров и размытия."""
        params = {
            "hsv_h": 0.2,
            "hsv_s": 1.5,
            "hsv_v": 1.2,
            "blur": 5,
            "noise": 10.0
        }
        aug_img, aug_boxes = AugmentationEngine.apply_transformations(
            self.test_img, self.test_boxes, params
        )
        self.assertEqual(aug_img.shape, self.test_img.shape)
        self.assertEqual(len(aug_boxes), 1)

    def test_weather_effects(self):
        """Проверка эффектов дождя и тумана."""
        rain_img, _ = AugmentationEngine.apply_transformations(
            self.test_img, self.test_boxes, {"weather": "rain"}
        )
        self.assertEqual(rain_img.shape, self.test_img.shape)

        fog_img, _ = AugmentationEngine.apply_transformations(
            self.test_img, self.test_boxes, {"weather": "fog"}
        )
        self.assertEqual(fog_img.shape, self.test_img.shape)


if __name__ == "__main__":
    unittest.main()
