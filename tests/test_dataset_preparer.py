import unittest
from unittest.mock import patch
import os
import tempfile
import numpy as np
from project.project_manager import Project
from project.dataset_preparer import prepare_detection_dataset, prepare_classification_dataset

class TestDatasetPreparer(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.images_dir = os.path.join(self.temp_dir.name, "images")
        self.project_file = os.path.join(self.temp_dir.name, "project.vf")
        self.export_dir = os.path.join(self.temp_dir.name, "export")
        os.makedirs(self.images_dir, exist_ok=True)
        os.makedirs(self.export_dir, exist_ok=True)

        for i in range(2):
            with open(os.path.join(self.images_dir, f"img_{i}.jpg"), 'w') as f:
                f.write("dummy")

        self.project = Project(self.project_file, images_dir=self.images_dir)
        self.project.load()
        self.project.set_annotations("img_0.jpg", [
            {"class": "car", "bbox": [10, 10, 20, 20]},
            {"class": "tree", "bbox": [50, 50, 100, 100], "polygon": [[50, 50], [100, 50], [100, 100], [50, 100]]}
        ], mode='main')
        self.project.set_annotations("img_1.jpg", [
            {"class": "car", "bbox": [0, 0, 100, 100]}
        ], mode='main')
        self.project.classes = ["car", "tree"]

    def tearDown(self):
        self.temp_dir.cleanup()

    @patch('cv2.imread')
    @patch('shutil.copy2')
    def test_detection_dataset_forced_boxes(self, mock_copy, mock_imread):
        mock_imread.return_value = np.zeros((200, 200, 3), dtype=np.uint8)

        prepare_detection_dataset(
            self.project,
            self.export_dir,
            train_ratio=1.0, val_ratio=0.0, test_ratio=0.0,
            task_type='detection'
        )

        label_file = os.path.join(self.export_dir, "labels", "train", "img_0.txt")
        self.assertTrue(os.path.exists(label_file))

        with open(label_file, 'r') as f:
            lines = f.readlines()
        self.assertEqual(len(lines), 2)

        for line in lines:
            parts = line.strip().split(' ')
            self.assertEqual(len(parts), 5, f"Detection dataset line must have 5 parts: {line}")

        yaml_file = os.path.join(self.export_dir, "data.yaml")
        self.assertTrue(os.path.exists(yaml_file))

    @patch('cv2.imread')
    @patch('shutil.copy2')
    def test_segmentation_dataset_forced_polygons(self, mock_copy, mock_imread):
        mock_imread.return_value = np.zeros((200, 200, 3), dtype=np.uint8)

        prepare_detection_dataset(
            self.project,
            self.export_dir,
            train_ratio=1.0, val_ratio=0.0, test_ratio=0.0,
            task_type='segmentation',
            seg_box_mode='convert'
        )

        label_file = os.path.join(self.export_dir, "labels", "train", "img_0.txt")
        self.assertTrue(os.path.exists(label_file))

        with open(label_file, 'r') as f:
            lines = f.readlines()
        self.assertEqual(len(lines), 2)

        for line in lines:
            parts = line.strip().split(' ')
            self.assertGreaterEqual(len(parts), 9, f"Segmentation line must have at least 9 parts: {line}")

    @patch('cv2.imread')
    @patch('cv2.imwrite')
    @patch('shutil.copy2')
    def test_classification_dataset_crops(self, mock_copy, mock_imwrite, mock_imread):
        mock_imread.return_value = np.zeros((200, 200, 3), dtype=np.uint8)
        mock_imwrite.return_value = True

        prepare_classification_dataset(
            self.project,
            self.export_dir,
            train_ratio=1.0, val_ratio=0.0, test_ratio=0.0,
            crop_boxes=True
        )

        classes_txt = os.path.join(self.export_dir, 'classes.txt')
        self.assertTrue(os.path.exists(classes_txt))
        with open(classes_txt, 'r', encoding='utf-8') as f:
            lines = f.read().splitlines()
        self.assertIn("car", lines)
        self.assertIn("tree", lines)

    @patch('cv2.imread')
    @patch('shutil.copy2')
    def test_classification_dataset_full(self, mock_copy, mock_imread):
        mock_imread.return_value = np.zeros((200, 200, 3), dtype=np.uint8)

        prepare_classification_dataset(
            self.project,
            self.export_dir,
            train_ratio=1.0, val_ratio=0.0, test_ratio=0.0,
            crop_boxes=False
        )

        classes_txt = os.path.join(self.export_dir, 'classes.txt')
        self.assertTrue(os.path.exists(classes_txt))

    @patch('cv2.imread')
    @patch('shutil.copy2')
    def test_dataset_preparer_with_auto_mode(self, mock_copy, mock_imread):
        mock_imread.return_value = np.zeros((200, 200, 3), dtype=np.uint8)

        self.project.set_annotations("img_0.jpg", [{"class": "ai_box", "bbox": [5, 5, 25, 25]}], mode='auto')

        prepare_detection_dataset(
            self.project,
            self.export_dir,
            train_ratio=1.0, val_ratio=0.0, test_ratio=0.0,
            mode='auto'
        )

        label_file = os.path.join(self.export_dir, "labels", "train", "img_0.txt")
        self.assertTrue(os.path.exists(label_file))

    def test_dataset_preparer_empty_dataset_handling(self):
        empty_project = Project(os.path.join(self.temp_dir.name, "empty.vf"), images_dir=self.images_dir)
        empty_project.load()

        with self.assertRaises(ValueError):
            prepare_detection_dataset(empty_project, self.export_dir)

        with self.assertRaises(ValueError):
            prepare_classification_dataset(empty_project, self.export_dir)

if __name__ == '__main__':
    unittest.main()
