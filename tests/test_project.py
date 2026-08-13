import unittest
import os
import tempfile
import json
from project.project_manager import Project

class TestProjectManager(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.images_dir = os.path.join(self.temp_dir.name, "images")
        self.project_file = os.path.join(self.temp_dir.name, "project.vf")
        os.makedirs(self.images_dir, exist_ok=True)

        for i in range(3):
            with open(os.path.join(self.images_dir, f"img_{i}.jpg"), 'w') as f:
                f.write("dummy")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_new_project_initialization_with_vf_path(self):
        proj = Project(self.project_file, images_dir=self.images_dir)
        self.assertFalse(os.path.exists(self.project_file))
        proj.load()
        self.assertEqual(len(proj.images_list), 3)
        self.assertEqual(proj.classes, ["unknown"])
        self.assertEqual(proj.class_hierarchy, ["unknown"])
        self.assertIn("unknown", proj.class_colors)

    def test_new_project_legacy_constructor_order(self):
        # Legacy positional args: (images_dir, annotations_file)
        legacy_file = os.path.join(self.temp_dir.name, "legacy_annotations.json")
        proj = Project(self.images_dir, legacy_file)
        self.assertEqual(proj.file_path, legacy_file)
        self.assertEqual(proj.images_dir, self.images_dir)
        self.assertEqual(proj.annotations_file, legacy_file)
        proj.load()
        self.assertEqual(len(proj.images_list), 3)

    def test_save_and_load_new_vf_format(self):
        proj = Project(self.project_file, images_dir=self.images_dir)
        proj.load()

        boxes_main = [{"class": "car", "bbox": [10, 10, 50, 50]}]
        boxes_auto = [{"class": "pedestrian", "bbox": [60, 60, 90, 90]}]

        proj.set_annotations("img_0.jpg", boxes_main, mode='main')
        proj.set_annotations("img_0.jpg", boxes_auto, mode='auto')
        proj.class_hierarchy = ["car", "pedestrian"]
        proj.save()

        self.assertTrue(os.path.exists(self.project_file))

        # Re-load in a separate instance
        proj2 = Project(self.project_file)
        proj2.load()

        self.assertEqual(proj2.images_dir, os.path.normpath(self.images_dir))
        self.assertEqual(len(proj2.get_annotations("img_0.jpg", mode='main')), 1)
        self.assertEqual(len(proj2.get_annotations("img_0.jpg", mode='auto')), 1)
        self.assertEqual(proj2.get_annotations("img_0.jpg", mode='main')[0]["class"], "car")
        self.assertEqual(proj2.get_annotations("img_0.jpg", mode='auto')[0]["class"], "pedestrian")
        self.assertIn("car", proj2.classes)
        self.assertIn("pedestrian", proj2.classes)

    def test_load_legacy_annotations_format(self):
        legacy_file = os.path.join(self.temp_dir.name, "legacy.json")
        legacy_data = {
            "annotations": {
                "img_0.jpg": [{"class": "truck", "bbox": [0, 0, 100, 100]}],
                "img_1.jpg": [{"class": "car", "bbox": [20, 20, 40, 40]}]
            },
            "class_hierarchy": ["truck", "car"],
            "class_colors": {"truck": "#ff0000", "car": "#00ff00"}
        }
        with open(legacy_file, 'w', encoding='utf-8') as f:
            json.dump(legacy_data, f)

        proj = Project(legacy_file, images_dir=self.images_dir)
        proj.load()

        self.assertEqual(len(proj.get_annotations("img_0.jpg", mode='main')), 1)
        self.assertEqual(proj.get_annotations("img_0.jpg", mode='main')[0]["class"], "truck")
        self.assertEqual(proj.class_colors["truck"], "#ff0000")
        self.assertIn("truck", proj.classes)
        self.assertIn("car", proj.classes)

    def test_load_raw_flat_dict_format(self):
        flat_file = os.path.join(self.temp_dir.name, "flat.json")
        flat_data = {
            "img_0.jpg": [{"class": "bus", "bbox": [10, 10, 80, 80]}],
            "img_1.jpg": [{"class": "bike", "bbox": [5, 5, 25, 25]}]
        }
        with open(flat_file, 'w', encoding='utf-8') as f:
            json.dump(flat_data, f)

        proj = Project(flat_file, images_dir=self.images_dir)
        proj.load()

        self.assertEqual(len(proj.get_annotations("img_0.jpg", mode='main')), 1)
        self.assertEqual(proj.get_annotations("img_0.jpg", mode='main')[0]["class"], "bus")
        self.assertIn("bus", proj.classes)
        self.assertIn("bike", proj.classes)

    def test_annotations_property_getter_setter(self):
        proj = Project(self.project_file, images_dir=self.images_dir)
        proj.load()

        # Setter via property
        proj.annotations = {
            "img_0.jpg": [{"class": "dog", "bbox": [0, 0, 10, 10]}],
            "img_1.jpg": [{"class": "cat", "bbox": [20, 20, 30, 30]}]
        }

        # Getter via property
        anns = proj.annotations
        self.assertIn("img_0.jpg", anns)
        self.assertEqual(anns["img_0.jpg"][0]["class"], "dog")
        self.assertEqual(anns["img_1.jpg"][0]["class"], "cat")

    def test_get_and_set_annotations_main_and_auto(self):
        proj = Project(self.project_file, images_dir=self.images_dir)
        proj.load()

        proj.set_annotations("img_0.jpg", [{"class": "sign", "bbox": [1, 2, 3, 4]}], mode='main')
        proj.set_annotations("img_0.jpg", [{"class": "light", "bbox": [5, 6, 7, 8]}], mode='auto')

        self.assertEqual(len(proj.get_annotations("img_0.jpg", mode='main')), 1)
        self.assertEqual(len(proj.get_annotations("img_0.jpg", mode='auto')), 1)
        self.assertEqual(proj.get_annotations("img_0.jpg", mode='main')[0]["class"], "sign")
        self.assertEqual(proj.get_annotations("img_0.jpg", mode='auto')[0]["class"], "light")

    def test_approve_auto_annotations(self):
        proj = Project(self.project_file, images_dir=self.images_dir)
        proj.load()

        proj.set_annotations("img_0.jpg", [{"class": "auto_detected", "bbox": [10, 10, 50, 50]}], mode='auto')
        self.assertEqual(len(proj.get_annotations("img_0.jpg", mode='main')), 0)
        self.assertEqual(len(proj.get_annotations("img_0.jpg", mode='auto')), 1)

        proj.approve_auto_annotations("img_0.jpg")

        self.assertEqual(len(proj.get_annotations("img_0.jpg", mode='main')), 1)
        self.assertEqual(len(proj.get_annotations("img_0.jpg", mode='auto')), 0)
        self.assertEqual(proj.get_annotations("img_0.jpg", mode='main')[0]["class"], "auto_detected")

    def test_delete_image(self):
        proj = Project(self.project_file, images_dir=self.images_dir)
        proj.load()

        proj.set_annotations("img_0.jpg", [{"class": "car", "bbox": [0, 0, 10, 10]}])
        self.assertIn("img_0.jpg", proj.images_list)

        proj.delete_image("img_0.jpg")
        self.assertNotIn("img_0.jpg", proj.images_list)
        self.assertNotIn("img_0.jpg", proj.images_data)

    def test_rename_class(self):
        proj = Project(self.project_file, images_dir=self.images_dir)
        proj.load()

        proj.set_annotations("img_0.jpg", [{"class": "old_name", "bbox": [0, 0, 10, 10]}], mode='main')
        proj.set_annotations("img_1.jpg", [{"class": "old_name", "bbox": [5, 5, 15, 15]}], mode='auto')
        proj.class_hierarchy = ["old_name", "other"]

        proj.rename_class("old_name", "new_name")

        self.assertEqual(proj.get_annotations("img_0.jpg", mode='main')[0]["class"], "new_name")
        self.assertEqual(proj.get_annotations("img_1.jpg", mode='auto')[0]["class"], "new_name")
        self.assertIn("new_name", proj.classes)
        self.assertNotIn("old_name", proj.classes)
        self.assertIn("new_name", proj.class_colors)

    def test_delete_class(self):
        proj = Project(self.project_file, images_dir=self.images_dir)
        proj.load()

        proj.set_annotations("img_0.jpg", [
            {"class": "to_remove", "bbox": [0, 0, 10, 10]},
            {"class": "to_keep", "bbox": [20, 20, 30, 30]}
        ], mode='main')

        proj.delete_class("to_remove")

        boxes = proj.get_annotations("img_0.jpg", mode='main')
        self.assertEqual(len(boxes), 1)
        self.assertEqual(boxes[0]["class"], "to_keep")
        self.assertNotIn("to_remove", proj.classes)

    def test_validate_data_fails_on_corrupt(self):
        proj = Project(self.project_file, images_dir=self.images_dir)
        self.assertFalse(proj._validate_data("plain text"))
        self.assertFalse(proj._validate_data(123))
        self.assertFalse(proj._validate_data({"annotations": "not_a_dict"}))
        self.assertFalse(proj._validate_data({"images": "not_a_dict"}))
        self.assertFalse(proj._validate_data({"class_colors": [1, 2, 3]}))
        self.assertFalse(proj._validate_data({"class_hierarchy": "not_a_list"}))
        self.assertFalse(proj._validate_data({"classes": "not_a_list"}))
        self.assertTrue(proj._validate_data({"images": {}, "classes": []}))

    def test_update_classes_from_hierarchy(self):
        proj = Project(self.project_file, images_dir=self.images_dir)
        proj.class_hierarchy = [
            "vehicle",
            {"name": "cars", "children": ["sedan", "suv"]},
            {"name": "heavy", "children": [{"name": "trucks", "children": ["semi", "pickup"]}]}
        ]
        proj.update_classes_from_hierarchy()
        self.assertEqual(proj.classes, ["cars", "heavy", "pickup", "sedan", "semi", "suv", "trucks", "vehicle"])

if __name__ == '__main__':
    unittest.main()
