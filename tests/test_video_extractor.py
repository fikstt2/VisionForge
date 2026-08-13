# tests/test_video_extractor.py
import unittest
import os
import shutil
import tempfile
import cv2
import numpy as np
from core.video_extractor import VideoExtractor


class TestVideoExtractor(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.video_path = os.path.join(self.temp_dir, "test_video.mp4")

        # Создаем синтетическое 1-секундное видео (25 кадров, 320x240)
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(self.video_path, fourcc, 25.0, (320, 240))
        for i in range(25):
            frame = np.zeros((240, 320, 3), dtype=np.uint8)
            # В середине видео меняем цвет для проверки смены сцен
            color = (0, 0, 255) if i < 12 else (255, 0, 0)
            cv2.rectangle(frame, (20, 20), (300, 220), color, -1)
            out.write(frame)
        out.release()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_get_video_info(self):
        """Проверка извлечения метаданных видео."""
        info = VideoExtractor.get_video_info(self.video_path)
        self.assertIsInstance(info, dict)
        self.assertEqual(info["width"], 320)
        self.assertEqual(info["height"], 240)
        self.assertGreaterEqual(info["total_frames"], 24)

    def test_extract_frames_interval(self):
        """Проверка извлечения каждого 5-го кадра."""
        out_dir = os.path.join(self.temp_dir, "frames_interval")
        extracted = VideoExtractor.extract_frames(
            video_path=self.video_path,
            output_dir=out_dir,
            step_type="interval",
            interval=5
        )
        self.assertGreaterEqual(len(extracted), 4)
        for f in extracted:
            self.assertTrue(os.path.exists(os.path.join(out_dir, f)))

    def test_extract_frames_scene_change(self):
        """Проверка детекции смены сцен."""
        out_dir = os.path.join(self.temp_dir, "frames_scene")
        extracted = VideoExtractor.extract_frames(
            video_path=self.video_path,
            output_dir=out_dir,
            step_type="scene",
            scene_threshold=15.0
        )
        # Должен извлечь как минимум первый кадр и кадр смены цвета
        self.assertGreaterEqual(len(extracted), 2)


if __name__ == "__main__":
    unittest.main()
