import os
import json
import cv2
import glob
from xml.etree import ElementTree as ET

def import_yolo(folder):
    """
    Импорт из YOLO формата.
    folder - папка, содержащая изображения и подпапку labels с txt-файлами (или txt рядом).
    Возвращает (annotations_dict, classes_list)
    """
    images_dir = folder
    labels_dir = os.path.join(folder, "labels")
    if not os.path.exists(labels_dir):
        labels_dir = folder  # пробуем искать txt рядом

    classes_file = os.path.join(folder, "classes.txt")
    classes = []
    if os.path.exists(classes_file):
        with open(classes_file, 'r') as f:
            classes = [line.strip() for line in f if line.strip()]

    annotations = {}
    for ext in ('*.jpg', '*.jpeg', '*.png', '*.bmp'):
        for img_path in glob.glob(os.path.join(images_dir, ext)):
            filename = os.path.basename(img_path)
            txt_name = os.path.splitext(filename)[0] + '.txt'
            txt_path = os.path.join(labels_dir, txt_name)
            if not os.path.exists(txt_path):
                continue
            img = cv2.imread(img_path)
            if img is None:
                continue
            h, w = img.shape[:2]
            boxes = []
            with open(txt_path, 'r') as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) != 5:
                        continue
                    cls_id = int(parts[0])
                    x_center = float(parts[1]) * w
                    y_center = float(parts[2]) * h
                    box_w = float(parts[3]) * w
                    box_h = float(parts[4]) * h
                    x1 = int(x_center - box_w / 2)
                    y1 = int(y_center - box_h / 2)
                    x2 = int(x_center + box_w / 2)
                    y2 = int(y_center + box_h / 2)
                    class_name = classes[cls_id] if cls_id < len(classes) else f"class_{cls_id}"
                    boxes.append({"bbox": [x1, y1, x2, y2], "class": class_name})
            if boxes:
                annotations[filename] = boxes
    # Собираем все уникальные классы из аннотаций, если classes.txt не полный
    if not classes:
        class_set = set()
        for boxes in annotations.values():
            for box in boxes:
                class_set.add(box["class"])
        classes = sorted(class_set)
    return annotations, classes

def import_coco(json_path):
    """
    Импорт из COCO JSON.
    json_path - путь к файлу аннотаций.
    Предполагается, что изображения находятся в той же папке, что и JSON.
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        coco = json.load(f)

    categories = {cat['id']: cat['name'] for cat in coco['categories']}
    images_info = {img['id']: img for img in coco['images']}

    annotations = {}
    for ann in coco['annotations']:
        img_id = ann['image_id']
        img_info = images_info.get(img_id)
        if not img_info:
            continue
        filename = os.path.basename(img_info['file_name'])
        x, y, w, h = ann['bbox']
        x2 = x + w
        y2 = y + h
        cat_id = ann['category_id']
        class_name = categories.get(cat_id, 'unknown')
        box = {"bbox": [int(x), int(y), int(x2), int(y2)], "class": class_name}
        annotations.setdefault(filename, []).append(box)

    classes = list(categories.values())
    return annotations, classes

def import_voc(folder):
    """
    Импорт из Pascal VOC.
    folder - папка с XML-файлами. Изображения предполагаются там же.
    """
    annotations = {}
    classes_set = set()
    for xml_path in glob.glob(os.path.join(folder, "*.xml")):
        tree = ET.parse(xml_path)
        root = tree.getroot()
        filename = root.find('filename').text
        size = root.find('size')
        if size is None:
            continue
        width = int(size.find('width').text)
        height = int(size.find('height').text)
        boxes = []
        for obj in root.findall('object'):
            name = obj.find('name').text
            bndbox = obj.find('bndbox')
            xmin = int(bndbox.find('xmin').text)
            ymin = int(bndbox.find('ymin').text)
            xmax = int(bndbox.find('xmax').text)
            ymax = int(bndbox.find('ymax').text)
            boxes.append({"bbox": [xmin, ymin, xmax, ymax], "class": name})
            classes_set.add(name)
        if boxes:
            annotations[filename] = boxes
    return annotations, sorted(classes_set)