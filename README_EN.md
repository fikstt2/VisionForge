# VisionForge 🚀

**VisionForge** is a powerful desktop tool for image annotation, YOLO model training, and real-time object detection.  
All-in-one: from dataset creation to training and inference — without leaving the interface.

*[Русская версия →](README.md)*

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PyQt5](https://img.shields.io/badge/GUI-PyQt5-green.svg)](https://www.riverbankcomputing.com/software/pyqt/)
[![OpenCV](https://img.shields.io/badge/OpenCV-4.x-brightgreen.svg)](https://opencv.org/)
[![YOLO](https://img.shields.io/badge/YOLO-Ultralytics-orange)](https://github.com/ultralytics/ultralytics)

---

## ✨ Features

- **Bounding Box & Polygon Annotation** — draw boxes and polygons, assign classes, drag vertices, undo (Ctrl+Z).
- **Class Hierarchy** — create groups (mega-classes), merge subclasses, assign colors. Full hierarchy is saved per project.
- **Auto-Annotation** — use a pretrained YOLO detector for rapid initial labeling of entire projects.
- **Batch Processing** — run detection on all images; results are saved in a separate auto-project.
- **Dataset Preparation** — flexible train/val/test split, class merging, cropping objects for classification. YOLO-compatible output.
- **YOLO Training** — configure hyperparameters, augmentation, run training from the GUI with live charts and logs.
- **Real-Time Detection** — screen overlay with object tracking and hotkeys.
- **Import/Export** — YOLO, COCO, Pascal VOC formats. Custom JSON with hierarchy and class colors.
- **Localization** — full Russian and English language support. Switch in Settings.
- **Project Statistics** — class distribution, dataset balance recommendations, CSV export.
- **Gallery** — search by filename, filter by class, adjustable thumbnail size (Small / Medium / Large).
- **Themes** — Dark (Indigo), Light, High Contrast.

---

## ⌨️ Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `N` | Force start drawing (even inside existing objects) |
| `B` | Switch to box mode |
| `P` | Switch to polygon mode |
| `T` | Next class |
| `D` | Delete selected box |
| `E` | Change class of selected box |
| `S` | Save |
| `A` | Auto-annotate current image |
| `F` / `G` | Previous / next image |
| `Ctrl+Z` | Undo |
| `Ctrl+D` | Delete current image |
| `F11` | Toggle fullscreen |
| `RMB` | Class management menu |

---

## 📦 Installation

### Option 1: Prebuilt Executable (Windows)

1. Download the latest release from [Releases](https://github.com/fikstt2/VisionForge/releases).
2. Extract the archive and run `VisionForge.exe`.

### Option 2: From Source (Python 3.9+)

```bash
git clone https://github.com/fikstt2/VisionForge.git
cd VisionForge
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

pip install -r requirements.txt
python ui/launcher.py
```

---

## 📁 Project Structure

```
VisionForge/
├── core/                    # Core: annotation widget, gallery, i18n, thumbnails
│   ├── annotation_widget.py # Annotation widget (boxes + polygons)
│   ├── gallery_dialog.py    # Image gallery
│   ├── i18n.py              # Localization system
│   └── thumbnail_bar.py     # Thumbnail carousel
├── detection/               # Detection and real-time overlay
├── locales/                 # Translation files (ru.json, en.json)
├── project/                 # Project manager, dataset preparation
├── ui/                      # Interface: main window, dialogs, settings
│   ├── main_window.py       # Main application window
│   ├── settings_dialog.py   # Settings dialog
│   ├── theme.py             # Themes (QSS stylesheets)
│   └── training_widget.py   # YOLO training widget
├── config.py                # Application configuration
├── requirements.txt         # Python dependencies
└── run_tests.py             # Test suite
```

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.
