# VisionForge 🚀

**VisionForge** is a professional desktop suite for smart image annotation, data augmentation, dataset quality control, YOLO model training, and production deployment.  
All-in-one: from raw video frame extraction and 1-click magic segmentation to embedding cluster maps, training, and real-time inference.

*[Русская версия →](README.md)*

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: GPL-3.0](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)
[![PyQt5](https://img.shields.io/badge/GUI-PyQt5-green.svg)](https://www.riverbankcomputing.com/software/pyqt/)
[![OpenCV](https://img.shields.io/badge/OpenCV-4.x-brightgreen.svg)](https://opencv.org/)
[![YOLO](https://img.shields.io/badge/YOLO-Ultralytics-orange)](https://github.com/ultralytics/ultralytics)

---

## ✨ Key Features

### 🪄 1. Smart 1-Click Magic Tool (`[M]`)
- **Single-click object segmentation:** click on any target object — the hybrid engine (adaptive ROI, FloodFill + multi-scale GrabCut / FastSAM / YOLO-seg) instantly constructs a tight polygon contour along pixel boundaries.
- **Polygon contour smoothing:** vertex optimization via Ramer–Douglas–Peucker algorithm (`approxPolyDP`) without losing detail.

### 🎞️ 2. Video Import & Frame Slicing
- Supported video formats: `.mp4`, `.avi`, `.mkv`, `.mov`.
- Extraction modes: frame interval, target FPS, or automatic scene change detection (Keyframes).

### 🚀 3. Track Interpolation Between Keyframes (`Ctrl+I`)
- Annotate objects on start and end keyframes — VisionForge automatically interpolates smooth trajectory bounding boxes and polygon vertices across all intermediate frames.

### 🎨 4. Interactive Augmentation Sandbox
- Live real-time preview of augmentations with interactive sliders:
  - **Geometry:** Rotation, Scale, X/Y translation, Horizontal and Vertical flips.
  - **Color:** Per-channel HSV shifts (Hue, Saturation, Value).
  - **Effects:** Gaussian Noise, Blur, Rain simulation, Fog, and Cutout masks.
- Automatic coordinate recalculation for boxes and polygons with 1-click "Save Copy to Dataset".

### 🔍 5. Dataset Deduplication & Quality Control (QA)
- **Perceptual Hashing (64-bit pHash):** rapid detection of near-identical frames and camera bursts via 2D DCT with similarity threshold (%) filtering.
- **Defect Detection:** automated detection of blurry frames (Laplacian variance), overexposed, and underexposed images with 1-click batch deletion.

### 🗺️ 6. Interactive Embedding Map (t-SNE / PCA Explorer)
- Extract 144-dimensional visual feature descriptors (spatial color histograms, gradient textures).
- 2D dimensionality reduction via fast **PCA** or nonlinear **t-SNE**.
- **Anomaly Detection:** automatic outlier detection (highlighted with red rings) to spot mislabeled classes, lighting artifacts, or rare camera angles.
- Interactive canvas: smooth zoom, panning, hover cards, and **instant double-click frame navigation**.

### ⚡ 7. Production Export & Standalone Inference Generator
- **YOLO Model Conversion:** export trained models to `ONNX` (FP16, dynamic batch shapes, ONNX Simplify), `TensorRT`, `OpenVINO`, and `CoreML`.
- **Standalone Python Inference Script:** generate standalone Python scripts for webcam, video file, or RTSP stream inference with live FPS overlays and video recording.

### 🎯 8. Annotation, Class Hierarchy & Training
- **Dual-layer Project Architecture (`.vf`):** separation between verified manual ground truth (`main`) and AI predictions (`auto`) with non-blocking toast approvals.
- **Class Hierarchy:** mega-classes, parent/child groupings, and custom color palettes.
- **Dataset Export:** YOLO (Detection / Segmentation / Classification), COCO JSON, Pascal VOC XML.
- **Integrated YOLO Training:** hyperparameter configuration, live metric plots, and real-time logs.

---

## ⌨️ Keyboard Shortcuts

| Key | Action |
|:---|:---|
| `M` | **Magic Mode (1-Click Segmentation)** |
| `B` | Switch to Rectangle (Box) Mode |
| `P` | Switch to Polygon Mode |
| `N` | Force start drawing a new object |
| `A` | Auto-annotate current image using loaded model |
| `T` | Switch active class to next |
| `F` / `G` | Previous / next image |
| `Ctrl + I` | **Open Track Interpolation Dialog** |
| `Ctrl + Z` | Undo last action |
| `Ctrl + D` | Delete current image from dataset |
| `D` | Delete selected box / polygon |
| `E` | Edit class of selected object |
| `S` | Save project |
| `Enter` / `Double Click` | Finish polygon creation |
| `Esc` | Cancel in-progress drawing |
| `F11` | Toggle fullscreen |
| `RMB` | Class management context menu |

---

## 📦 Installation & Quickstart

### Quickstart from Source (Python 3.9+)

```bash
# 1. Clone repository
git clone https://github.com/fikstt2/VisionForge.git
cd VisionForge

# 2. Create and activate virtual environment
python -m venv .venv

# Windows:
.venv\Scripts\activate
# Linux / macOS:
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Launch VisionForge
python main.py
# or on Windows:
run.bat
```

### Run Unit Tests

```bash
python run_tests.py
```

---

## 📁 Project Structure

```
VisionForge/
├── core/                        # Core application modules
│   ├── annotation_widget.py     # Annotation canvas (OpenGL/QPainter, boxes, polygons, magic)
│   ├── smart_segmenter.py       # 1-click segmentation engine (FastSAM / GrabCut / Adaptive ROI)
│   ├── video_extractor.py       # Video slicing module (Interval / FPS / Scene Change)
│   ├── track_interpolator.py    # Trajectory interpolation algorithm for boxes and polygons
│   ├── augmentation_engine.py   # Image and annotation augmentation matrix engine
│   ├── dataset_deduplicator.py  # 64-bit pHash deduplication & QA defect detection
│   ├── embedding_explorer.py    # Visual feature descriptors, t-SNE / PCA & outlier finder
│   ├── gallery_dialog.py        # Dataset gallery with search and filters
│   ├── thumbnail_bar.py         # Thumbnail carousel
│   └── i18n.py                  # Localization engine (RU/EN)
├── detection/                   # Real-time detection & desktop overlay
├── locales/                     # Localization files (ru.json, en.json)
├── project/                     # .vf project manager, importers and exporters
│   ├── project_manager.py       # Monolithic .vf storage manager
│   ├── dataset_preparer.py      # Dataset splitter for YOLO / COCO / VOC
│   ├── exporters.py             # Annotation exporters
│   └── importers.py             # Annotation importers
├── ui/                          # Graphical interface (PyQt5)
│   ├── main_window.py           # Main editor window
│   ├── embedding_map_dialog.py  # Interactive 2D t-SNE/PCA embedding map
│   ├── augmentation_sandbox_dialog.py # Interactive augmentation sandbox
│   ├── deduplication_dialog.py  # Duplicate & defect finder dialog
│   ├── track_interpolation_dialog.py  # Track interpolation dialog
│   ├── video_extractor_dialog.py      # Video extractor dialog
│   ├── production_export_dialog.py    # Production exporter (ONNX / TensorRT / OpenVINO)
│   ├── inference_generator_dialog.py  # Standalone Python inference generator
│   ├── project_hub_dialog.py    # Project hub dialog with recents
│   ├── statistics_dialog.py     # Class distribution statistics & analytics
│   └── training_widget.py       # YOLO training widget
├── tests/                       # Unit test suite (57 tests)
├── main.py                      # Application entrypoint
├── run.bat                      # Windows quickstart batch script
└── requirements.txt             # Python dependencies
```

---

## 📄 License

This project is licensed under the **GNU General Public License v3.0 (GPLv3)**. See the [LICENSE](LICENSE) file for details.
