# tests/test_production_export.py
import unittest
import ast
from ui.inference_generator_dialog import generate_python_inference_code


class TestProductionExport(unittest.TestCase):
    def test_generate_python_inference_code_syntax(self):
        """Проверка того, что сгенерированный Python-скрипт является синтаксически валидным кодом."""
        code = generate_python_inference_code(
            model_path="test_weights.pt",
            source_type="Webcam (0)",
            source_path="0",
            conf=0.6,
            iou=0.5,
            show_fps=True,
            save_output=True,
            output_path="test_out.mp4"
        )
        self.assertIsInstance(code, str)
        self.assertIn("def run_inference", code)
        self.assertIn("test_weights.pt", code)
        self.assertIn("0.6", code)

        # Проверка AST компиляции синтаксиса
        parsed_ast = ast.parse(code)
        self.assertIsNotNone(parsed_ast)

    def test_generate_python_inference_code_with_video(self):
        """Проверка генерации скрипта для видеофайла."""
        code = generate_python_inference_code(
            model_path="model.onnx",
            source_type="Video (.mp4)",
            source_path="sample.mp4",
            conf=0.25,
            iou=0.45,
            show_fps=False,
            save_output=False
        )
        self.assertIn("sample.mp4", code)
        self.assertIn("model.onnx", code)
        parsed = ast.parse(code)
        self.assertIsNotNone(parsed)


if __name__ == "__main__":
    unittest.main()
