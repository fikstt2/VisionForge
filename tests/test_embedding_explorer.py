# tests/test_embedding_explorer.py
import unittest
import numpy as np
from core.embedding_explorer import EmbeddingExplorer


class TestEmbeddingExplorer(unittest.TestCase):
    def test_extract_image_features(self):
        """Проверка длины и L2-нормализации вектора признаков."""
        img = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        feat = EmbeddingExplorer.extract_image_features(img)
        self.assertEqual(len(feat), 144)
        norm = np.linalg.norm(feat)
        self.assertAlmostEqual(norm, 1.0, places=4)

    def test_compute_pca_2d(self):
        """Проверка 2D проекции PCA."""
        feats = np.random.randn(10, 144).astype(np.float32)
        proj = EmbeddingExplorer.compute_pca_2d(feats)
        self.assertEqual(proj.shape, (10, 2))
        self.assertLessEqual(np.max(np.abs(proj)), 1.01)

    def test_compute_tsne_2d(self):
        """Проверка 2D проекции t-SNE."""
        feats = np.random.randn(8, 144).astype(np.float32)
        proj = EmbeddingExplorer.compute_tsne_2d(feats, perplexity=3.0, n_iter=50)
        self.assertEqual(proj.shape, (8, 2))
        self.assertLessEqual(np.max(np.abs(proj)), 1.01)


if __name__ == "__main__":
    unittest.main()
