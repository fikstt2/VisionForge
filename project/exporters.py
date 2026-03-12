# project/exporters.py
import os
import json
import cv2
from xml.etree import ElementTree as ET
from xml.dom import minidom
from config import VERSION
def export_yolo(project, output_dir):
    """Экспорт в формат YOLO (txt-файлы в папке labels)."""
    images_dir = project.images_dir
    os.makedirs(output_dir, exist_ok=True)
    labels_dir = os.path.join(output_dir, "labels")
    os.makedirs(labels_dir, exist_ok=True)

    # Создаём файл с классами
    classes_file = os.path.join(output_dir, "classes.txt")
    with open(classes_file, 'w', encoding='utf-8') as f:
        f.write("\n".join(project.classes))

    class_to_id = {cls: i for i, cls in enumerate(project.classes)}

    for filename in project.images_list:
        boxes = project.get_annotations(filename)
        if not boxes:
            continue
        img_path = os.path.join(images_dir, filename)
        img = cv2.imread(img_path)
        if img is None:
            continue
        h, w = img.shape[:2]

        label_lines = []
        for box in boxes:
            cls_name = box["class"]
            if cls_name not in class_to_id:
                continue
            cls_id = class_to_id[cls_name]
            x1, y1, x2, y2 = box["bbox"]
            x_center = (x1 + x2) / 2 / w
            y_center = (y1 + y2) / 2 / h
            width = (x2 - x1) / w
            height = (y2 - y1) / h
            label_lines.append(f"{cls_id} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}")

        if label_lines:
            txt_name = os.path.splitext(filename)[0] + ".txt"
            txt_path = os.path.join(labels_dir, txt_name)
            with open(txt_path, 'w') as f:
                f.write("\n".join(label_lines))
    print(f"YOLO export completed: {output_dir}")

def export_coco(project, output_file):
    """Экспорт в COCO JSON."""
    images_dir = project.images_dir
    class_to_id = {cls: i+1 for i, cls in enumerate(project.classes)}  # COCO id с 1

    coco = {
        "info": {
            "description": "Exported from VisionForge",
            "version": VERSION,
            "year": 2025,
            "contributor": "",
            "date_created": ""
        },
        "licenses": [],
        "images": [],
        "annotations": [],
        "categories": [{"id": i+1, "name": cls, "supercategory": "object"} for i, cls in enumerate(project.classes)]
    }

    ann_id = 1
    for img_id, filename in enumerate(project.images_list):
        img_path = os.path.join(images_dir, filename)
        img = cv2.imread(img_path)
        if img is None:
            continue
        h, w = img.shape[:2]
        coco["images"].append({
            "id": img_id,
            "file_name": filename,
            "width": w,
            "height": h,
            "license": 0,
            "date_captured": ""
        })

        boxes = project.get_annotations(filename)
        for box in boxes:
            cls_name = box["class"]
            if cls_name not in class_to_id:
                continue
            x1, y1, x2, y2 = box["bbox"]
            x, y = float(x1), float(y1)
            width, height = float(x2 - x1), float(y2 - y1)
            coco["annotations"].append({
                "id": ann_id,
                "image_id": img_id,
                "category_id": class_to_id[cls_name],
                "bbox": [x, y, width, height],
                "area": width * height,
                "iscrowd": 0
            })
            ann_id += 1

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(coco, f, indent=2, ensure_ascii=False)
    print(f"COCO export completed: {output_file}")

def export_voc(project, output_dir):
    """Экспорт в Pascal VOC XML."""
    images_dir = project.images_dir
    os.makedirs(output_dir, exist_ok=True)

    for filename in project.images_list:
        img_path = os.path.join(images_dir, filename)
        img = cv2.imread(img_path)
        if img is None:
            continue
        h, w, d = img.shape

        boxes = project.get_annotations(filename)
        annotation = ET.Element("annotation")
        ET.SubElement(annotation, "folder").text = os.path.basename(output_dir)
        ET.SubElement(annotation, "filename").text = filename
        size = ET.SubElement(annotation, "size")
        ET.SubElement(size, "width").text = str(w)
        ET.SubElement(size, "height").text = str(h)
        ET.SubElement(size, "depth").text = str(d)
        ET.SubElement(annotation, "segmented").text = "0"

        for box in boxes:
            obj = ET.SubElement(annotation, "object")
            ET.SubElement(obj, "name").text = box["class"]
            ET.SubElement(obj, "pose").text = "Unspecified"
            ET.SubElement(obj, "truncated").text = "0"
            ET.SubElement(obj, "difficult").text = "0"
            bbox_elem = ET.SubElement(obj, "bndbox")
            x1, y1, x2, y2 = box["bbox"]
            ET.SubElement(bbox_elem, "xmin").text = str(x1)
            ET.SubElement(bbox_elem, "ymin").text = str(y1)
            ET.SubElement(bbox_elem, "xmax").text = str(x2)
            ET.SubElement(bbox_elem, "ymax").text = str(y2)

        # Красивое форматирование
        xml_str = minidom.parseString(ET.tostring(annotation)).toprettyxml(indent="  ")
        xml_name = os.path.splitext(filename)[0] + ".xml"
        xml_path = os.path.join(output_dir, xml_name)
        with open(xml_path, 'w', encoding='utf-8') as f:
            f.write(xml_str)

    print(f"Pascal VOC export completed: {output_dir}")