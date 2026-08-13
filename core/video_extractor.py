# core/video_extractor.py
import os
import cv2
import numpy as np
import logging

logger = logging.getLogger(__name__)


class VideoExtractor:
    """Универсальный инструмент извлечения кадров из видеофайлов."""

    @staticmethod
    def get_video_info(video_path: str) -> dict:
        """Получение метаданных о видеофайле."""
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Видеофайл не найден: {video_path}")

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Не удалось открыть видеофайл: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        duration_sec = total_frames / fps if fps > 0 else 0.0

        fourcc_int = int(cap.get(cv2.CAP_PROP_FOURCC))
        fourcc_str = "".join([chr((fourcc_int >> 8 * i) & 0xFF) for i in range(4)])

        cap.release()

        return {
            "fps": round(fps, 2),
            "total_frames": total_frames,
            "width": width,
            "height": height,
            "duration_sec": round(duration_sec, 2),
            "codec": fourcc_str.strip()
        }

    @staticmethod
    def extract_frames(
        video_path: str,
        output_dir: str,
        prefix: str = None,
        step_type: str = "interval",
        interval: int = 5,
        target_fps: float = 2.0,
        scene_threshold: float = 30.0,
        max_frames: int = 1000,
        progress_callback = None,
        cancel_check = None
    ) -> list:
        """Извлечение кадров из видеофайла.
        
        step_type:
            - 'interval': каждый N-й кадр (interval)
            - 'fps': заданная частота извлечения в секунду (target_fps)
            - 'scene': извлечение при смене сцены (scene_threshold)
            - 'all': каждый кадр
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Файл не найден: {video_path}")

        os.makedirs(output_dir, exist_ok=True)
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Не удалось открыть видео: {video_path}")

        source_fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1

        if not prefix:
            base_name = os.path.splitext(os.path.basename(video_path))[0]
            prefix = f"{base_name}_frame"

        extracted_files = []
        frame_idx = 0
        saved_count = 0

        # Вычисляем шаг для режима FPS
        if step_type == "fps":
            step = max(1, int(round(source_fps / max(0.1, target_fps))))
        elif step_type == "interval":
            step = max(1, interval)
        else:
            step = 1

        prev_gray = None

        while cap.isOpened():
            if cancel_check and cancel_check():
                break

            if saved_count >= max_frames:
                break

            ret, frame = cap.read()
            if not ret:
                break

            should_save = False

            if step_type in ["interval", "fps"]:
                if frame_idx % step == 0:
                    should_save = True
            elif step_type == "all":
                should_save = True
            elif step_type == "scene":
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                # Сжимаем для быстрого вычисления разницы
                small_gray = cv2.resize(gray, (160, 90))
                if prev_gray is None:
                    should_save = True
                else:
                    diff = cv2.absdiff(small_gray, prev_gray)
                    mean_diff = np.mean(diff)
                    if mean_diff >= scene_threshold:
                        should_save = True
                prev_gray = small_gray

            if should_save:
                out_filename = f"{prefix}_{frame_idx:06d}.jpg"
                out_path = os.path.join(output_dir, out_filename)
                cv2.imwrite(out_path, frame, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
                extracted_files.append(out_filename)
                saved_count += 1

            frame_idx += 1
            if progress_callback and frame_idx % 5 == 0:
                progress_pct = int(min(100, (frame_idx / total_frames) * 100))
                progress_callback(progress_pct, saved_count, frame_idx)

        cap.release()
        if progress_callback:
            progress_callback(100, saved_count, frame_idx)

        return extracted_files
