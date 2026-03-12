# core/utils.py
import cv2
import numpy as np
import platform
import os
from collections import OrderedDict
from PIL import Image, ImageDraw, ImageFont
from PyQt5.QtGui import QImage, QPixmap

import config

class LimitedSizeDict(OrderedDict):
    def __init__(self, maxsize=200, *args, **kwargs):
        self.maxsize = maxsize
        super().__init__(*args, **kwargs)

    def __setitem__(self, key, value):
        if key in self:
            self.move_to_end(key)
        super().__setitem__(key, value)
        if len(self) > self.maxsize:
            self.popitem(last=False)

    def __getitem__(self, key):
        value = super().__getitem__(key)
        self.move_to_end(key)
        return value

def get_default_font_path():
    """Возвращает путь к системному шрифту в зависимости от ОС."""
    system = platform.system()
    if system == "Windows":
        candidates = [
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/seguiemj.ttf",
            "C:/Windows/Fonts/calibri.ttf"
        ]
    elif system == "Linux":
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/TTF/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
        ]
    elif system == "Darwin":  # macOS
        candidates = [
            "/System/Library/Fonts/Helvetica.ttc",
            "/Library/Fonts/Arial.ttf"
        ]
    else:
        candidates = []
    for path in candidates:
        if os.path.exists(path):
            return path
    return None

def draw_text_cv2(img, text, pos, color=(0, 255, 0), font_scale=0.5):
    """Рисует текст на изображении с поддержкой кириллицы через PIL."""
    img_pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(img_pil)
    font_size = int(font_scale * 30)
    try:
        font = ImageFont.truetype(config.FONT_PATH, font_size)
    except Exception as e:
        print(f"Ошибка загрузки шрифта {config.FONT_PATH}: {e}. Использую шрифт по умолчанию.")
        font = ImageFont.load_default()
    draw.text(pos, text, font=font, fill=color[::-1])
    return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)

def cv2_to_qpixmap(cv_img):
    """Конвертирует OpenCV BGR изображение в QPixmap."""
    rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
    h, w, ch = rgb_image.shape
    bytes_per_line = ch * w
    qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
    return QPixmap.fromImage(qt_image)

def qpixmap_to_cv2(pixmap):
    """Конвертирует QPixmap в OpenCV BGR изображение."""
    qimage = pixmap.toImage()
    qimage = qimage.convertToFormat(QImage.Format_RGB888)
    width = qimage.width()
    height = qimage.height()
    ptr = qimage.bits()
    ptr.setsize(qimage.byteCount())
    arr = np.array(ptr).reshape(height, width, 3)  # RGB
    return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)