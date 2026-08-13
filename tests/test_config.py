import unittest
import os
import json
import tempfile
import config
from project.project_manager import Project

class TestConfig(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_config_file = os.path.join(self.temp_dir.name, "test_settings.json")
        self.original_config_file = config.CONFIG_FILE
        config.CONFIG_FILE = self.test_config_file

    def tearDown(self):
        config.CONFIG_FILE = self.original_config_file
        self.temp_dir.cleanup()

    def test_load_default_config_if_missing(self):
        self.assertFalse(os.path.exists(config.CONFIG_FILE))
        cfg = config.load_config()
        self.assertIn("theme", cfg)
        self.assertIn("language", cfg)
        self.assertEqual(cfg["recent_projects"], [])
        self.assertEqual(cfg["theme"], "Тёмная")

    def test_load_and_merge_config(self):
        user_config = {"theme": "Светлая", "some_custom_key": 42}
        with open(config.CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(user_config, f)

        cfg = config.load_config()
        self.assertEqual(cfg["theme"], "Светлая")
        self.assertIn("language", cfg)
        self.assertEqual(cfg["some_custom_key"], 42)

    def test_broken_json_fallback_with_backup(self):
        with open(config.CONFIG_FILE, 'w', encoding='utf-8') as f:
            f.write("{ invalid json content: true, ")

        cfg = config.load_config()
        self.assertIn("theme", cfg)
        self.assertEqual(cfg["recent_projects"], [])
        self.assertTrue(os.path.exists(config.CONFIG_FILE + ".bak"))

    def test_recent_projects_adding_string_path(self):
        p1 = os.path.join(self.temp_dir.name, "proj1.vf")
        p2 = os.path.join(self.temp_dir.name, "proj2.vf")
        config.add_recent_project(p1)
        config.add_recent_project(p2)

        recents = config.get_recent_projects()
        self.assertEqual(len(recents), 2)
        self.assertEqual(recents[0]["name"], "proj2")
        self.assertEqual(recents[1]["name"], "proj1")

    def test_recent_projects_adding_dict(self):
        p1 = {"json_path": os.path.join(self.temp_dir.name, "proj1.vf"), "name": "Custom 1", "description": "Desc 1"}
        config.add_recent_project(p1)

        recents = config.get_recent_projects()
        self.assertEqual(len(recents), 1)
        self.assertEqual(recents[0]["name"], "Custom 1")
        self.assertEqual(recents[0]["description"], "Desc 1")

    def test_recent_projects_adding_project_obj(self):
        img_dir = os.path.join(self.temp_dir.name, "images")
        os.makedirs(img_dir, exist_ok=True)
        img_file = os.path.join(img_dir, "sample.jpg")
        with open(img_file, 'wb') as f:
            f.write(b"fake_image_bytes")

        vf_path = os.path.join(self.temp_dir.name, "project.vf")
        proj = Project(vf_path, images_dir=img_dir)
        proj.images_list = ["sample.jpg"]

        config.add_recent_project(vf_path, project=proj)
        recents = config.get_recent_projects()
        self.assertEqual(len(recents), 1)
        self.assertEqual(recents[0]["name"], "project")
        self.assertEqual(recents[0]["thumbnail"], img_file)

    def test_recent_projects_duplicate_handling(self):
        p1 = os.path.join(self.temp_dir.name, "proj1.vf")
        config.add_recent_project(p1)
        config.add_recent_project({"json_path": p1, "name": "Updated Proj 1", "description": "New Desc"})

        recents = config.get_recent_projects()
        self.assertEqual(len(recents), 1)
        self.assertEqual(recents[0]["name"], "Updated Proj 1")
        self.assertEqual(recents[0]["description"], "New Desc")

    def test_recent_projects_update_thumbnail_and_description(self):
        p1 = os.path.join(self.temp_dir.name, "proj1.vf")
        config.add_recent_project(p1)

        thumb = os.path.join(self.temp_dir.name, "thumb.jpg")
        config.update_recent_project_thumbnail(p1, thumb)
        config.update_recent_project_description(p1, "My Description")

        recents = config.get_recent_projects()
        self.assertEqual(len(recents), 1)
        self.assertEqual(recents[0]["thumbnail"], thumb)
        self.assertEqual(recents[0]["description"], "My Description")

    def test_recent_projects_legacy_string_format_migration(self):
        legacy_config = {
            "recent_projects": [
                os.path.join(self.temp_dir.name, "legacy1.vf"),
                os.path.join(self.temp_dir.name, "legacy2.vf"),
            ]
        }
        with open(config.CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(legacy_config, f)

        recents = config.get_recent_projects()
        self.assertEqual(len(recents), 2)
        self.assertIsInstance(recents[0], dict)
        self.assertEqual(recents[0]["name"], "legacy1")
        self.assertEqual(recents[1]["name"], "legacy2")

    def test_save_config(self):
        cfg = {"theme": "Светлая", "cls_conf": 0.8}
        config.save_config(cfg)
        self.assertTrue(os.path.exists(config.CONFIG_FILE))
        with open(config.CONFIG_FILE, 'r', encoding='utf-8') as f:
            saved = json.load(f)
        self.assertEqual(saved["theme"], "Светлая")
        self.assertEqual(saved["cls_conf"], 0.8)

if __name__ == '__main__':
    unittest.main()
