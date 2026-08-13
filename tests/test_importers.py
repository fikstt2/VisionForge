import unittest
from unittest.mock import patch
import os
import tempfile
import json
import numpy as np
from xml.etree import ElementTree as ET
from project.importers import import_yolo, import_coco, import_voc

class TestImporters(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_dir = os.path.join(self.temp_dir.name, "data")
        os.makedirs(self.data_dir, exist_ok=True)

    def tearDown(self):
        self.temp_dir.cleanup()

    @patch('cv2.imread')
    def test_import_yolo_boxes_and_polygons(self, mock_imread):
        mock_imread.return_value = np.zeros((100, 200, 3), dtype=np.uint8)  # h=100, w=200

        # Create dummy image files
        img1 = os.path.join(self.data_dir, "img1.jpg")
        img2 = os.path.join(self.data_dir, "img2.jpg")
        with open(img1, 'wb') as f: f.write(b"dummy")
        with open(img2, 'wb') as f: f.write(b"dummy")

        # Create classes.txt
        classes_file = os.path.join(self.data_dir, "classes.txt")
        with open(classes_file, 'w', encoding='utf-8') as f:
            f.write("car\ntree\nperson\n")

        # Labels folder
        labels_dir = os.path.join(self.data_dir, "labels")
        os.makedirs(labels_dir, exist_ok=True)

        # img1: 1 standard box: cls=0, cx=0.5, cy=0.5, w=0.2, h=0.4
        with open(os.path.join(labels_dir, "img1.txt"), 'w') as f:
            f.write("0 0.5 0.5 0.2 0.4\n")

        # img2: 1 segmentation polygon: cls=1, pts: (0.1, 0.1), (0.4, 0.1), (0.4, 0.4), (0.1, 0.4)
        with open(os.path.join(labels_dir, "img2.txt"), 'w') as f:
            f.write("1 0.1 0.1 0.4 0.1 0.4 0.4 0.1 0.4\n")

        annotations, classes = import_yolo(self.data_dir)

        self.assertIn("car", classes)
        self.assertIn("tree", classes)
        self.assertIn("img1.jpg", annotations)
        self.assertIn("img2.jpg", annotations)

        # Check box 1 coordinates:
        # cx=0.5*200=100, cy=0.5*100=50, w=0.2*200=40, h=0.4*100=40
        # x1 = 100 - 20 = 80, y1 = 50 - 20 = 30, x2 = 100 + 20 = 120, y2 = 50 + 20 = 70
        box1 = annotations["img1.jpg"][0]
        self.assertEqual(box1["class"], "car")
        self.assertEqual(box1["bbox"], [80, 30, 120, 70])

        # Check polygon in box 2
        box2 = annotations["img2.jpg"][0]
        self.assertEqual(box2["class"], "tree")
        self.assertIn("polygon", box2)
        self.assertEqual(len(box2["polygon"]), 4)
        self.assertEqual(box2["polygon"][0], [20, 10])

    def test_import_coco_json(self):
        coco_path = os.path.join(self.data_dir, "coco.json")
        coco_data = {
            "categories": [
                {"id": 1, "name": "cat"},
                {"id": 2, "name": "dog"}
            ],
            "images": [
                {"id": 101, "file_name": "cat1.jpg", "width": 640, "height": 480},
                {"id": 102, "file_name": "dog1.png", "width": 800, "height": 600}
            ],
            "annotations": [
                {
                    "id": 1,
                    "image_id": 101,
                    "category_id": 1,
                    "bbox": [50, 60, 100, 120],
                    "segmentation": [[50, 60, 150, 60, 150, 180, 50, 180]]
                },
                {
                    "id": 2,
                    "image_id": 102,
                    "category_id": 2,
                    "bbox": [10, 20, 200, 300]
                }
            ]
        }
        with open(coco_path, 'w', encoding='utf-8') as f:
            json.dump(coco_data, f)

        annotations, classes = import_coco(coco_path)

        self.assertIn("cat", classes)
        self.assertIn("dog", classes)
        self.assertIn("cat1.jpg", annotations)
        self.assertIn("dog1.png", annotations)

        cat_ann = annotations["cat1.jpg"][0]
        self.assertEqual(cat_ann["class"], "cat")
        self.assertEqual(cat_ann["bbox"], [50, 60, 150, 180])
        self.assertIn("polygon", cat_ann)
        self.assertEqual(cat_ann["polygon"][0], [50, 60])

        dog_ann = annotations["dog1.png"][0]
        self.assertEqual(dog_ann["class"], "dog")
        self.assertEqual(dog_ann["bbox"], [10, 20, 210, 320])

    def test_import_pascal_voc(self):
        voc_file = os.path.join(self.data_dir, "sample.xml")
        root = ET.Element("annotation")
        ET.SubElement(root, "filename").text = "sample.jpg"
        size = ET.SubElement(root, "size")
        ET.SubElement(size, "width").text = "640"
        ET.SubElement(size, "height").text = "480"
        ET.SubElement(size, "depth").text = "3"

        obj1 = ET.SubElement(root, "object")
        ET.SubElement(obj1, "name").text = "bicycle"
        bndbox1 = ET.SubElement(obj1, "bndbox")
        ET.SubElement(bndbox1, "xmin").text = "10"
        ET.SubElement(bndbox1, "ymin").text = "20"
        ET.SubElement(bndbox1, "xmax").text = "100"
        ET.SubElement(bndbox1, "ymax").text = "200"

        tree = ET.ElementTree(root)
        tree.write(voc_file, encoding='utf-8', xml_declaration=True)

        annotations, classes = import_voc(self.data_dir)

        self.assertIn("bicycle", classes)
        self.assertIn("sample.jpg", annotations)
        box = annotations["sample.jpg"][0]
        self.assertEqual(box["class"], "bicycle")
        self.assertEqual(box["bbox"], [10, 20, 100, 200])

if __name__ == '__main__':
    unittest.main()
