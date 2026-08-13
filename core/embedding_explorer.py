# core/embedding_explorer.py
import os
import cv2
import numpy as np
import logging

logger = logging.getLogger(__name__)


class EmbeddingExplorer:
    """Модуль извлечения эмбеддингов, снижения размерности (PCA, t-SNE) и поиска аномалий."""

    @classmethod
    def extract_image_features(cls, img_rgb: np.ndarray) -> np.ndarray:
        """Извлечение компактного L2-нормализованного вектора признаков (144-D) для изображения."""
        if img_rgb is None or img_rgb.size == 0:
            return np.zeros(144, dtype=np.float32)

        # 1. Пространственная цветовая гистограмма в HSV (3x3 сетка по 8 бинов на H, S, V = 72 фичи)
        hsv = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2HSV)
        h, w = hsv.shape[:2]

        color_feats = []
        for i in range(3):
            for j in range(3):
                y1, y2 = int(i * h / 3), int((i + 1) * h / 3)
                x1, x2 = int(j * w / 3), int((j + 1) * w / 3)
                cell = hsv[y1:y2, x1:x2]
                if cell.size > 0:
                    h_hist = cv2.calcHist([cell], [0], None, [8], [0, 180]).flatten()
                    s_hist = cv2.calcHist([cell], [1], None, [4], [0, 256]).flatten()
                    v_hist = cv2.calcHist([cell], [2], None, [4], [0, 256]).flatten()
                    norm_hist = np.concatenate([h_hist, s_hist, v_hist])
                    norm_hist /= (np.sum(norm_hist) + 1e-6)
                    color_feats.append(norm_hist)
                else:
                    color_feats.append(np.zeros(16, dtype=np.float32))

        color_vector = np.concatenate(color_feats)  # 9 * 16 = 144 фичи

        # Нормализуем по L2 норме
        norm = np.linalg.norm(color_vector)
        if norm > 1e-6:
            color_vector = color_vector / norm

        return color_vector.astype(np.float32)

    @classmethod
    def compute_pca_2d(cls, features: np.ndarray) -> np.ndarray:
        """Снижение размерности до 2D с помощью метода главных компонент (PCA)."""
        N = len(features)
        if N == 0:
            return np.zeros((0, 2), dtype=np.float32)
        if N == 1:
            return np.zeros((1, 2), dtype=np.float32)

        # Центрирование данных
        mean = np.mean(features, axis=0)
        centered = features - mean

        # Сингулярное разложение (SVD)
        try:
            _, _, vt = np.linalg.svd(centered, full_matrices=False)
            projected = np.dot(centered, vt[:2].T)
        except Exception:
            projected = centered[:, :2] if centered.shape[1] >= 2 else np.zeros((N, 2))

        # Масштабирование в диапазон [-1.0, 1.0]
        max_val = np.max(np.abs(projected))
        if max_val > 1e-6:
            projected = projected / max_val

        return projected.astype(np.float32)

    @classmethod
    def compute_tsne_2d(cls, features: np.ndarray, perplexity: float = 30.0, n_iter: int = 250) -> np.ndarray:
        """Снижение размерности до 2D с помощью стохастического вложения соседей t-SNE."""
        N = len(features)
        if N <= 3:
            return cls.compute_pca_2d(features)

        # Пытаемся использовать sklearn если доступен, либо встроенный градиентный спуск
        try:
            from sklearn.manifold import TSNE
            perp = min(perplexity, max(1.0, float(N - 1) / 3.0))
            tsne = TSNE(n_components=2, perplexity=perp, n_iter=n_iter, random_state=42, init='pca')
            projected = tsne.fit_transform(features)
        except Exception:
            # Быстрый градиентный t-SNE
            projected = cls._simple_tsne(features, perplexity=min(perplexity, N - 1), n_iter=n_iter)

        max_val = np.max(np.abs(projected))
        if max_val > 1e-6:
            projected = projected / max_val

        return projected.astype(np.float32)

    @classmethod
    def _simple_tsne(cls, X: np.ndarray, perplexity: float = 10.0, n_iter: int = 150) -> np.ndarray:
        """Облегченный t-SNE алгоритм на чистом NumPy."""
        N = X.shape[0]
        # Вычисляем матрицу попарных евклидовых расстояний
        sum_X = np.sum(np.square(X), 1)
        D = np.add(np.add(-2 * np.dot(X, X.T), sum_X).T, sum_X)
        D = np.maximum(D, 0.0)

        # Расчет вероятностей P
        P = np.exp(-D / (2 * (perplexity ** 2)))
        np.fill_diagonal(P, 0.0)
        P = (P + P.T) / (2 * np.sum(P) + 1e-12)
        P = np.maximum(P, 1e-12)

        # Инициализация Y из PCA
        Y = cls.compute_pca_2d(X) * 0.1
        gains = np.ones((N, 2))
        iY = np.zeros((N, 2))
        lr = 200.0

        for _ in range(n_iter):
            # t-Student q_ij
            sum_Y = np.sum(np.square(Y), 1)
            num = 1.0 / (1.0 + np.add(np.add(-2 * np.dot(Y, Y.T), sum_Y).T, sum_Y))
            np.fill_diagonal(num, 0.0)
            Q = num / (np.sum(num) + 1e-12)
            Q = np.maximum(Q, 1e-12)

            # Градиент
            PQ = P - Q
            dY = np.zeros((N, 2))
            for i in range(N):
                dY[i, :] = np.sum(np.tile(PQ[:, i] * num[:, i], (2, 1)).T * (Y[i, :] - Y), 0)

            # Обновление позиций с импульсом
            iY = 0.8 * iY - lr * dY
            Y = Y + iY
            Y = Y - np.mean(Y, 0)

        return Y

    @classmethod
    def analyze_project_embeddings(
        cls,
        project,
        method: str = "pca",
        progress_callback = None
    ) -> dict:
        """Комплексный анализ проекта: извлечение векторов, 2D проекция и детекция выбросов."""
        if not project or not project.images_list:
            return {"points": [], "classes": []}

        image_list = project.images_list
        total = len(image_list)
        features_list = []
        metadata_list = []
        classes_set = set()

        for idx, filename in enumerate(image_list):
            full_path = os.path.join(project.images_dir, filename)
            boxes = project.get_annotations(filename, mode="main")
            
            # Определяем доминирующий класс на изображении
            if boxes:
                cls_name = boxes[0].get("class", "Unannotated")
            else:
                cls_name = "Unannotated"
            classes_set.add(cls_name)

            if os.path.exists(full_path):
                img_bgr = cv2.imread(full_path)
                if img_bgr is not None:
                    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
                    feat = cls.extract_image_features(img_rgb)
                else:
                    feat = np.zeros(144, dtype=np.float32)
            else:
                feat = np.zeros(144, dtype=np.float32)

            features_list.append(feat)
            metadata_list.append({
                "filename": filename,
                "class": cls_name,
                "box_count": len(boxes)
            })

            if progress_callback and idx % 5 == 0:
                progress_callback(int((idx / max(1, total)) * 60))

        features_np = np.array(features_list, dtype=np.float32)

        # 2D Проекция
        if method == "tsne":
            coords_2d = cls.compute_tsne_2d(features_np)
        else:
            coords_2d = cls.compute_pca_2d(features_np)

        if progress_callback:
            progress_callback(85)

        # Детекция выбросов относительно центроидов классов
        class_centroids = {}
        for cls_name in classes_set:
            cls_indices = [i for i, m in enumerate(metadata_list) if m["class"] == cls_name]
            if len(cls_indices) >= 3:
                cls_feats = features_np[cls_indices]
                centroid = np.mean(cls_feats, axis=0)
                dists = np.linalg.norm(cls_feats - centroid, axis=1)
                mean_dist = np.mean(dists)
                std_dist = np.std(dists)
                class_centroids[cls_name] = (centroid, mean_dist, std_dist)

        points = []
        for i in range(len(metadata_list)):
            meta = metadata_list[i]
            cls_name = meta["class"]
            is_outlier = False
            score = 0.0

            if cls_name in class_centroids:
                centroid, mean_d, std_d = class_centroids[cls_name]
                dist = float(np.linalg.norm(features_np[i] - centroid))
                score = round(dist, 3)
                if std_d > 1e-4 and dist > (mean_d + 1.8 * std_d):
                    is_outlier = True

            points.append({
                "x": float(coords_2d[i, 0]),
                "y": float(coords_2d[i, 1]),
                "filename": meta["filename"],
                "class": cls_name,
                "box_count": meta["box_count"],
                "is_outlier": is_outlier,
                "score": score
            })

        if progress_callback:
            progress_callback(100)

        return {
            "points": points,
            "classes": sorted(list(classes_set))
        }
