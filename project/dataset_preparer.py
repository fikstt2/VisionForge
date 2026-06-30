# project/dataset_preparer.py
import os
import shutil
import random
import cv2
from collections import defaultdict

def prepare_detection_dataset(project, output_dir, train_ratio=0.8, val_ratio=0.2, test_ratio=0.0,
                              class_mapping=None, excluded_classes=None, task_type='detection',
                              seg_box_mode='exclude', progress_callback=None):
    """
    Подготавливает датасет для детекции / сегментации в формате YOLO.

    :param project: объект Project (с полями images_dir, annotations, classes)
    :param output_dir: корневая папка для датасета
    :param train_ratio: доля train
    :param val_ratio: доля val
    :param test_ratio: доля test (если 0, test не создаётся)
    :param class_mapping: словарь {старое_имя: новое_имя} для объединения классов
    :param excluded_classes: множество исходных классов, которые полностью исключаются
    :param seg_box_mode: поведение с bbox-аннотациями при сегментации:
        'exclude' — пропустить бокс без полигона (default, рекомендуется)
        'convert' — преобразовать bbox в прямоугольный полигон из 4 вершин
        'keep'    — использовать bbox как есть (только для опытных)
    """
    if class_mapping is None:
        class_mapping = {}
    if excluded_classes is None:
        excluded_classes = set()

    # Определяем новый список классов (уникальные значения mapping + оставшиеся старые, кроме исключённых)
    new_classes_set = set()
    for old_cls in project.classes:
        if old_cls in excluded_classes:
            continue
        new_cls = class_mapping.get(old_cls, old_cls)
        new_classes_set.add(new_cls)
    new_classes = sorted(new_classes_set)
    new_class_to_id = {cls: idx for idx, cls in enumerate(new_classes)}

    # Собираем все изображения, у которых есть аннотации, и фильтруем боксы
    valid_images = []
    image_valid_boxes = {}  # img_name -> list of valid boxes (after mapping & exclusion)

    for img_name in project.images_list:
        boxes = project.get_annotations(img_name)
        if not boxes:
            continue
        valid_boxes = []
        for box in boxes:
            old_cls = box['class']
            if old_cls in excluded_classes:
                continue
            new_cls = class_mapping.get(old_cls, old_cls)
            if new_cls not in new_class_to_id:
                # такого не должно быть, но на всякий случай пропускаем
                continue
            # преобразуем класс
            box_copy = box.copy()
            box_copy['class'] = new_cls
            valid_boxes.append(box_copy)
        if valid_boxes:
            valid_images.append(img_name)
            image_valid_boxes[img_name] = valid_boxes

    if not valid_images:
        raise ValueError("Нет изображений с аннотациями после применения исключений и объединения классов.")

    # Перемешиваем и разбиваем
    random.shuffle(valid_images)
    total = len(valid_images)
    train_end = int(total * train_ratio)
    val_end = train_end + int(total * val_ratio)

    train_images = valid_images[:train_end]
    val_images = valid_images[train_end:val_end]
    test_images = valid_images[val_end:] if test_ratio > 0 else []

    # Создаём папки
    subsets = [('train', train_images), ('val', val_images)]
    if test_images:
        subsets.append(('test', test_images))

    total_to_process = len(train_images) + len(val_images) + len(test_images)
    processed_count = 0

    for subset_name, img_list in subsets:
        images_subdir = os.path.join(output_dir, 'images', subset_name)
        labels_subdir = os.path.join(output_dir, 'labels', subset_name)
        os.makedirs(images_subdir, exist_ok=True)
        os.makedirs(labels_subdir, exist_ok=True)

        for img_name in img_list:
            processed_count += 1
            if progress_callback:
                progress_callback(processed_count, total_to_process)
            
            src_img = os.path.join(project.images_dir, img_name)
            dst_img = os.path.join(images_subdir, img_name)
            shutil.copy2(src_img, dst_img)

            # Создаём файл разметки
            txt_name = os.path.splitext(img_name)[0] + '.txt'
            txt_path = os.path.join(labels_subdir, txt_name)
            boxes = image_valid_boxes[img_name]
            img = cv2.imread(src_img)
            if img is None:
                continue
            h, w = img.shape[:2]

            with open(txt_path, 'w', encoding='utf-8') as f:
                for box in boxes:
                    cls_name = box['class']
                    cls_id = new_class_to_id[cls_name]
                    if task_type == 'segmentation':
                        # Bug #3 fix: handle seg_box_mode correctly
                        has_polygon = 'polygon' in box and box['polygon']
                        has_bbox = 'bbox' in box
                        if has_polygon:
                            pts = box['polygon']
                        elif has_bbox and seg_box_mode == 'convert':
                            # Convert bbox to 4-point rectangular polygon
                            x1, y1, x2, y2 = box['bbox']
                            pts = [[x1, y1], [x2, y1], [x2, y2], [x1, y2]]
                        elif has_bbox and seg_box_mode == 'keep':
                            # Use bbox corners as degenerate polygon
                            x1, y1, x2, y2 = box['bbox']
                            pts = [[x1, y1], [x2, y1], [x2, y2], [x1, y2]]
                        else:
                            # 'exclude' or no usable data — skip this annotation
                            continue
                        coords = []
                        for pt in pts:
                            coords.append(f"{pt[0] / w:.6f}")
                            coords.append(f"{pt[1] / h:.6f}")
                        f.write(f"{cls_id} {' '.join(coords)}\n")
                    else:
                        # Детекция: всегда записываем bbox (даже если есть полигон)
                        if 'bbox' not in box:
                            # Derive bbox from polygon if available
                            if 'polygon' in box and box['polygon']:
                                xs = [p[0] for p in box['polygon']]
                                ys = [p[1] for p in box['polygon']]
                                x1, y1, x2, y2 = min(xs), min(ys), max(xs), max(ys)
                            else:
                                continue
                        else:
                            x1, y1, x2, y2 = box['bbox']
                        x_center = (x1 + x2) / 2 / w
                        y_center = (y1 + y2) / 2 / h
                        width = (x2 - x1) / w
                        height = (y2 - y1) / h
                        f.write(f"{cls_id} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}\n")

    # Создаём data.yaml
    yaml_path = os.path.join(output_dir, 'data.yaml')
    with open(yaml_path, 'w', encoding='utf-8') as f:
        f.write(f"path: {output_dir}\n")
        f.write(f"train: images/train\n")
        f.write(f"val: images/val\n")
        if test_images:
            f.write(f"test: images/test\n")
        f.write(f"nc: {len(new_classes)}\n")
        f.write(f"names: {new_classes}\n")

    return len(train_images), len(val_images), len(test_images)


def prepare_classification_dataset(project, output_dir, train_ratio=0.8, val_ratio=0.2, test_ratio=0.0,
                                   class_mapping=None, excluded_classes=None,
                                   crop_boxes=True, multiple_boxes_handling='first',
                                   progress_callback=None):
    """
    Подготавливает датасет для классификации.

    :param project: объект Project
    :param output_dir: корневая папка для датасета
    :param train_ratio, val_ratio, test_ratio: пропорции выборок
    :param class_mapping: словарь {старое_имя: новое_имя} для объединения классов
    :param excluded_classes: множество исходных классов, которые исключаются
    :param crop_boxes: если True, каждый бокс вырезается и сохраняется как отдельное изображение.
                       Если False, сохраняется целое изображение, а класс определяется по первому неисключённому боксу.
    :param multiple_boxes_handling: как поступать при нескольких боксах на изображении (если crop_boxes=False):
        'first' - использовать класс первого неисключённого бокса,
        'skip' - пропускать такие изображения,
        'warn' - использовать первый и выдавать предупреждение.
    """
    if class_mapping is None:
        class_mapping = {}
    if excluded_classes is None:
        excluded_classes = set()

    # Определяем новый список классов (уникальные значения mapping + оставшиеся старые, кроме исключённых)
    new_classes_set = set()
    for old_cls in project.classes:
        if old_cls in excluded_classes:
            continue
        new_cls = class_mapping.get(old_cls, old_cls)
        new_classes_set.add(new_cls)
    new_classes = sorted(new_classes_set)

    os.makedirs(output_dir, exist_ok=True)

    # Если crop_boxes=True, то каждый неисключённый бокс становится отдельным образцом
    if crop_boxes:
        samples = []  # список кортежей (img_data, class_name, out_name)
        for img_name in project.images_list:
            boxes = project.get_annotations(img_name)
            if not boxes:
                continue
            src_img = os.path.join(project.images_dir, img_name)
            for idx, box in enumerate(boxes):
                old_cls = box['class']
                if old_cls in excluded_classes:
                    continue
                new_cls = class_mapping.get(old_cls, old_cls)
                if new_cls not in new_classes_set:
                    continue
                base, ext = os.path.splitext(img_name)
                crop_name = f"{base}_{new_cls}_{idx}{ext}"
                # Сохраняем путь и координаты бокса вместо самого изображения
                samples.append(((src_img, box['bbox']), new_cls, crop_name))
    else:
        # Работаем с целыми изображениями
        samples = []  # список кортежей (img_path, class_name, out_name)
        skipped_no_boxes = 0
        skipped_multiple = 0
        for img_name in project.images_list:
            boxes = project.get_annotations(img_name)
            if not boxes:
                skipped_no_boxes += 1
                continue
            # Отфильтровываем исключённые классы
            valid_boxes = [box for box in boxes if box['class'] not in excluded_classes]
            if not valid_boxes:
                skipped_no_boxes += 1
                continue
            # Определяем класс
            src_img = os.path.join(project.images_dir, img_name)
            if len(valid_boxes) == 1:
                old_cls = valid_boxes[0]['class']
                new_cls = class_mapping.get(old_cls, old_cls)
                if new_cls in new_classes_set:
                    samples.append((src_img, new_cls, img_name))
            else:
                if multiple_boxes_handling == 'skip':
                    skipped_multiple += 1
                    continue
                elif multiple_boxes_handling in ('first', 'warn'):
                    old_cls = valid_boxes[0]['class']
                    new_cls = class_mapping.get(old_cls, old_cls)
                    if multiple_boxes_handling == 'warn':
                        print(f"Предупреждение: изображение {img_name} содержит {len(valid_boxes)} неисключённых боксов, использован класс {new_cls}")
                    src_img = os.path.join(project.images_dir, img_name)
                    samples.append((src_img, new_cls, img_name))
                else:
                    raise ValueError(f"Неизвестное multiple_boxes_handling: {multiple_boxes_handling}")

    if not samples:
        raise ValueError("Нет подходящих образцов для классификации.")

    # Группируем по классам для стратификации
    class_to_samples = defaultdict(list)
    for sample, cls, name in samples:
        class_to_samples[cls].append((sample, name))

    # Перемешиваем внутри классов
    for cls in class_to_samples:
        random.shuffle(class_to_samples[cls])

    # Функция разбиения списка
    def split_list(lst, train_ratio, val_ratio):
        n = len(lst)
        train_end = int(n * train_ratio)
        val_end = train_end + int(n * val_ratio)
        return lst[:train_end], lst[train_end:val_end], lst[val_end:]

    # Распределяем по выборкам
    train_samples = []  # (sample, cls, name)
    val_samples = []
    test_samples = []

    for cls, items in class_to_samples.items():
        train, val, test = split_list(items, train_ratio, val_ratio)
        train_samples.extend([(s, cls, n) for s, n in train])
        val_samples.extend([(s, cls, n) for s, n in val])
        test_samples.extend([(s, cls, n) for s, n in test])

    # Перемешиваем итоговые списки
    random.shuffle(train_samples)
    random.shuffle(val_samples)
    random.shuffle(test_samples)

    # Создаём структуру папок
    subsets = [('train', train_samples), ('val', val_samples)]
    if test_samples:
        subsets.append(('test', test_samples))

    total_to_process = len(train_samples) + len(val_samples) + len(test_samples)
    processed_count = 0

    for subset_name, sample_list in subsets:
        for sample, cls, name in sample_list:
            processed_count += 1
            if progress_callback:
                progress_callback(processed_count, total_to_process)
            
            class_dir = os.path.join(output_dir, subset_name, cls)
            os.makedirs(class_dir, exist_ok=True)
            dst_path = os.path.join(class_dir, name)
            
            if isinstance(sample, str):  # путь к полному изображению
                shutil.copy2(sample, dst_path)
            elif isinstance(sample, tuple):  # (путь, bbox) для кропа
                src_path, (x1, y1, x2, y2) = sample
                img = cv2.imread(src_path)
                if img is not None:
                    crop = img[y1:y2, x1:x2]
                    if crop.size > 0:
                        cv2.imwrite(dst_path, crop)

    # Создаём файл с классами
    classes_txt = os.path.join(output_dir, 'classes.txt')
    with open(classes_txt, 'w', encoding='utf-8') as f:
        f.write("\n".join(new_classes))

    return len(train_samples), len(val_samples), len(test_samples)