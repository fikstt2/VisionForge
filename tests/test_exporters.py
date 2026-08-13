import unittest
from unittest.mock import patch
import os
import tempfile
import json
import numpy as np
from xml.etree import ElementTree as ET
from project.project_manager import Project
from project.exporters import export_coco, export_voc, export_yolo

class TestExporters(unittest.TestCase):
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
        ], mode='main')
        self.project.set_annotations("img_1.jpg", [
            {"class": "car", "bbox": [0, 0, 100, 100]},
            {"class": "tree", "polygon": [[50, 50], [100, 50], [100, 100], [50, 100]]}
        ], mode='main')
        self.project.classes = ["car", "tree"]

    def tearDown(self):
        self.temp_dir.cleanup()

    @patch('cv2.imread')
    def test_export_coco(self, mock_imread):
        mock_imread.return_value = np.zeros((200, 200, 3), dtype=np.uint8)

        outfile = os.path.join(self.export_dir, "coco.json")
        export_coco(self.project, outfile)

        self.assertTrue(os.path.exists(outfile))

        with open(outfile, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self.assertIn("images", data)
        self.assertIn("annotations", data)
        self.assertIn("categories", data)

        self.assertEqual(len(data["images"]), 2)
        self.assertEqual(len(data["annotations"]), 3)
        self.assertEqual(len(data["categories"]), 2)

        # COCO Category IDs must start from 1
        cat_ids = [cat["id"] for cat in data["categories"]]
        self.assertNotIn(0, cat_ids)
        self.assertIn(1, cat_ids)

        # Verify polygon-only annotation converted to bbox properly
        tree_ann = [a for a in data["annotations"] if a["category_id"] == cat_ids[1]][0]
        self.assertEqual(tree_ann["bbox"], [50.0, 50.0, 50.0, 50.0])

    @patch('cv2.imread')
    def test_export_voc(self, mock_imread):
        mock_imread.return_value = np.zeros((200, 200, 3), dtype=np.uint8)

        export_voc(self.project, self.export_dir)

        xml_file1 = os.path.join(self.export_dir, "img_0.xml")
        xml_file2 = os.path.join(self.export_dir, "img_1.xml")
        self.assertTrue(os.path.exists(xml_file1))
        self.assertTrue(os.path.exists(xml_file2))

        tree1 = ET.parse(xml_file1)
        root1 = tree1.getroot()
        self.assertEqual(root1.tag, "annotation")

        objects1 = root1.findall("object")
        self.assertEqual(len(objects1), 1)
        self.assertEqual(objects1[0].find("name").text, "car")

        tree2 = ET.parse(xml_file2)
        root2 = tree2.getroot()
        objects2 = root2.findall("object")
        self.assertEqual(len(objects2), 2)
        names = [o.find("name").text for o in objects2]
        self.assertIn("car", names)
        self.assertIn("tree", names)

    @patch('cv2.imread')
    def test_export_yolo(self, mock_imread):
        mock_imread.return_value = np.zeros((200, 200, 3), dtype=np.uint8)

        export_yolo(self.project, self.export_dir)

        classes_file = os.path.join(self.export_dir, "classes.txt")
        self.assertTrue(os.path.exists(classes_file))
        with open(classes_file, 'r', encoding='utf-8') as f:
            classes = f.read().splitlines()
        self.assertEqual(classes, ["car", "tree"])

        labels_dir = os.path.join(self.export_dir, "labels")
        self.assertTrue(os.path.exists(os.path.join(labels_dir, "img_0.txt")))
        self.assertTrue(os.path.exists(os.path.join(labels_dir, "img_1.txt")))

        with open(os.path.join(labels_dir, "img_1.txt"), 'r') as f:
            lines = f.readlines()
        self.assertEqual(len(lines), 2)

if __name__ == '__main__':
    unittest.main()
