# core/type_dialog.py
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                             QInputDialog, QMessageBox, QColorDialog, QGroupBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QPixmap, QIcon
from ui.class_hierarchy_widget import ClassHierarchyWidget
from ui.theme import get_current_theme_style
from collections import defaultdict
from core.i18n import tr

class TypeDialog(QDialog):
    def __init__(self, project, current_class, parent=None):
        super().__init__(parent)
        self.project = project
        self.current_class = current_class
        self.result_class = None

        self.setWindowTitle(tr("Управление классами"))
        self.setModal(True)
        self.setMinimumSize(600, 500)
        self.setStyleSheet(get_current_theme_style())

        layout = QVBoxLayout(self)

        tree_group = QGroupBox(tr("Иерархия классов"))
        tree_layout = QVBoxLayout()

        btn_layout = QHBoxLayout()
        self.add_group_btn = QPushButton(tr("+ Группа"))
        self.add_group_btn.clicked.connect(self.add_group)
        self.add_class_btn = QPushButton(tr("+ Класс"))
        self.add_class_btn.clicked.connect(self.add_class)
        self.delete_btn = QPushButton(tr("Удалить"))
        self.delete_btn.clicked.connect(self.delete_selected)
        self.rename_btn = QPushButton(tr("Переименовать"))
        self.rename_btn.clicked.connect(self.rename_selected)
        self.color_btn = QPushButton(tr("Изменить цвет"))
        self.color_btn.clicked.connect(self.change_color_selected)
        btn_layout.addWidget(self.add_group_btn)
        btn_layout.addWidget(self.add_class_btn)
        btn_layout.addWidget(self.delete_btn)
        btn_layout.addWidget(self.rename_btn)
        btn_layout.addWidget(self.color_btn)
        btn_layout.addStretch()
        tree_layout.addLayout(btn_layout)

        self.tree = ClassHierarchyWidget()
        self.tree.setHeaderLabels([tr("Класс / Группа"), tr("Количество")])
        self.tree.setColumnWidth(0, 300)
        self.tree.setColumnWidth(1, 80)
        self.tree.setDragEnabled(True)
        self.tree.setAcceptDrops(True)
        self.tree.setDropIndicatorShown(True)
        self.tree.setDragDropMode(self.tree.InternalMove)
        self.tree.itemClicked.connect(self.on_item_clicked)
        self.tree.itemDoubleClicked.connect(self.on_item_double_clicked)
        self.tree.hierarchy_changed.connect(self.on_hierarchy_changed)
        self.tree.delete_class_requested.connect(self.on_delete_class_requested)
        tree_layout.addWidget(self.tree)

        tree_group.setLayout(tree_layout)
        layout.addWidget(tree_group)

        btn_ok_cancel = QHBoxLayout()
        self.ok_btn = QPushButton(tr("OK"))
        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn = QPushButton(tr("Отмена"))
        self.cancel_btn.clicked.connect(self.reject)
        btn_ok_cancel.addStretch()
        btn_ok_cancel.addWidget(self.ok_btn)
        btn_ok_cancel.addWidget(self.cancel_btn)
        layout.addLayout(btn_ok_cancel)

        self.reload_tree()

    def reload_tree(self):
        counts = defaultdict(int)
        
        # Исправлено: Считаем объекты из монолитной структуры images_data
        for img_name, modes in self.project.images_data.items():
            # Учитываем боксы и из ручной ('main'), и из автоматической ('auto') веток
            for mode_key in ["main", "auto"]:
                for box in modes.get(mode_key, []):
                    cls = box.get('class', 'unknown')
                    counts[cls] += 1

        self.tree.populate_from_hierarchy(
            self.project.class_hierarchy,
            self.project.class_colors,
            counts
        )
        if self.current_class:
            self.select_class(self.current_class)

    def select_class(self, class_name):
        def search(item):
            if item.data(0, Qt.UserRole) == "class" and item.text(0) == class_name:
                self.tree.setCurrentItem(item)
                self.tree.scrollToItem(item)
                return True
            for i in range(item.childCount()):
                if search(item.child(i)):
                    return True
            return False
        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            if search(root.child(i)):
                break

    def on_item_clicked(self, item, column):
        if item.data(0, Qt.UserRole) == "class":
            self.result_class = item.text(0)

    def on_item_double_clicked(self, item, column):
        if item.data(0, Qt.UserRole) == "class":
            self.change_color(item)
        else:
            self.rename_item(item)

    def on_hierarchy_changed(self):
        pass

    def on_delete_class_requested(self, class_name):
        self.select_class(class_name)
        self.delete_selected()

    def add_group(self):
        name, ok = QInputDialog.getText(self, tr("Новая группа"), tr("Введите название группы:"))
        if ok and name.strip():
            self.tree.add_group(name.strip())
            self.on_hierarchy_changed()

    def add_class(self):
        name, ok = QInputDialog.getText(self, tr("Новый класс"), tr("Введите имя класса:"))
        if not ok or not name.strip():
            return
        name = name.strip()
        if self.class_exists(name):
            QMessageBox.warning(self, tr("Ошибка"), f"{tr('Класс')} '{name}' {tr('уже существует.')}")
            return

        parent_item = self.tree.currentItem()
        if parent_item and parent_item.data(0, Qt.UserRole) == "group":
            self._add_class_item(parent_item, name)
        else:
            root = self.tree.invisibleRootItem()
            self._add_class_item(root, name)
        self.on_hierarchy_changed()

    def _add_class_item(self, parent, class_name):
        color = self.project.class_colors.get(class_name, "#ffffff")
        pixmap = QPixmap(14, 14)
        pixmap.fill(QColor(color))
        item = self.tree._add_class_item(parent, class_name)
        item.setIcon(0, QIcon(pixmap))
        return item

    def class_exists(self, name):
        def search(item):
            if item.data(0, Qt.UserRole) == "class" and item.text(0) == name:
                return True
            for i in range(item.childCount()):
                if search(item.child(i)):
                    return True
            return False
        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            if search(root.child(i)):
                return True
        return False

    def delete_selected(self):
        item = self.tree.currentItem()
        if not item:
            return

        if item.data(0, Qt.UserRole) == "group":
            reply = QMessageBox.question(self, tr("Удаление группы"),
                                         f"{tr('Удалить группу')} '{item.text(0)}' {tr('и всё содержимое?')}",
                                         QMessageBox.Yes | QMessageBox.No)
            if reply != QMessageBox.Yes:
                return
            parent = item.parent() or self.tree.invisibleRootItem()
            parent.removeChild(item)
            self.on_hierarchy_changed()
        else:  # класс
            class_name = item.text(0)
            if hasattr(self.parent(), 'delete_class'):
                success = self.parent().delete_class(class_name)
                if success:
                    self.reload_tree()
            else:
                parent = item.parent() or self.tree.invisibleRootItem()
                parent.removeChild(item)
                self.on_hierarchy_changed()

    def rename_selected(self):
        item = self.tree.currentItem()
        if not item:
            return
        new_name, ok = QInputDialog.getText(self, tr("Переименование"),
                                            tr("Новое имя:"), text=item.text(0))
        if ok and new_name.strip():
            old_name = item.text(0)
            if item.data(0, Qt.UserRole) == "class":
                if self.class_exists(new_name.strip()) and new_name.strip() != old_name:
                    QMessageBox.warning(self, tr("Ошибка"), f"{tr('Класс')} '{new_name.strip()}' {tr('уже существует.')}")
                    return
            item.setText(0, new_name.strip())
            self.on_hierarchy_changed()

    def change_color_selected(self):
        item = self.tree.currentItem()
        if item and item.data(0, Qt.UserRole) == "class":
            self.change_color(item)

    def change_color(self, item):
        class_name = item.text(0)
        current_color = self.project.class_colors.get(class_name, "#ffffff")
        color = QColorDialog.getColor(QColor(current_color), self,
                                      f"{tr('Выберите цвет для класса')} {class_name}")
        if color.isValid():
            self.project.class_colors[class_name] = color.name()
            pixmap = QPixmap(14, 14)
            pixmap.fill(color)
            item.setIcon(0, QIcon(pixmap))
            self.on_hierarchy_changed()

    def accept(self):
        self.project.class_hierarchy = self.tree.export_to_hierarchy()
        self.project.update_classes_from_hierarchy()
        super().accept()