# tests/test_track_interpolator.py
import unittest
from core.track_interpolator import TrackInterpolator


class TestTrackInterpolator(unittest.TestCase):
    def test_interpolate_bbox(self):
        """Проверка линейной интерполяции координат bounding-box."""
        box_a = [10, 10, 50, 50]
        box_b = [110, 110, 150, 150]

        # Середина пути (t=0.5)
        mid = TrackInterpolator.interpolate_bbox(box_a, box_b, 0.5)
        self.assertEqual(mid, [60, 60, 100, 100])

        # Старт и финиш
        start = TrackInterpolator.interpolate_bbox(box_a, box_b, 0.0)
        self.assertEqual(start, box_a)
        finish = TrackInterpolator.interpolate_bbox(box_a, box_b, 1.0)
        self.assertEqual(finish, box_b)

    def test_resample_polygon(self):
        """Проверка ресэмплинга полигона."""
        square = [[0, 0], [100, 0], [100, 100], [0, 100]]
        resampled = TrackInterpolator.resample_polygon(square, target_count=12)
        self.assertEqual(len(resampled), 12)
        for pt in resampled:
            self.assertEqual(len(pt), 2)

    def test_interpolate_polygon(self):
        """Проверка интерполяции полигонов разной длины вершин."""
        poly_a = [[10, 10], [50, 10], [50, 50], [10, 50]]
        poly_b = [[110, 110], [170, 110], [180, 150], [150, 180], [110, 160]]

        inter = TrackInterpolator.interpolate_polygon(poly_a, poly_b, 0.5)
        self.assertIsInstance(inter, list)
        self.assertGreaterEqual(len(inter), 4)

    def test_interpolate_object_lists(self):
        """Проверка интерполяции списков объектов на 3 промежуточных кадра."""
        boxes_start = [{"bbox": [0, 0, 10, 10], "class": "car"}]
        boxes_end = [{"bbox": [40, 40, 50, 50], "class": "car"}]

        steps = TrackInterpolator.interpolate_object_lists(boxes_start, boxes_end, num_steps=3)
        self.assertEqual(len(steps), 3)

        # Проверяем шаг 1 (t=0.25) -> x1 = 0 + 40*0.25 = 10
        self.assertEqual(steps[0][0]["bbox"], [10, 10, 20, 20])
        # Проверяем шаг 2 (t=0.50) -> x1 = 0 + 40*0.50 = 20
        self.assertEqual(steps[1][0]["bbox"], [20, 20, 30, 30])
        # Проверяем шаг 3 (t=0.75) -> x1 = 0 + 40*0.75 = 30
        self.assertEqual(steps[2][0]["bbox"], [30, 30, 40, 40])


if __name__ == "__main__":
    unittest.main()
