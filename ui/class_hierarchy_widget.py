# ui/class_hierarchy_widget.py
from PyQt5.QtWidgets import (QTreeWidget, QTreeWidgetItem, QMenu, QInputDialog,
                             QMessageBox, QColorDialog, QAbstractItemView)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QIcon, QPixmap

class ClassHierarchyWidget(QTreeWidget):
    """Дерево для отображения и редактирования иерархии классов."""
    class_selected = pyqtSignal(str)          # имя класса (не группы)
    color_change_requested = pyqtSignal(str)  # имя класса
    hierarchy_changed = pyqtSignal()          # структура изменилась (переименование, перемещение)
    delete_class_requested = pyqtSignal(str)  # запрос на удаление класса

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderLabels(["Класс / Группа", "Счётчик"])
        self.setColumnWidth(0, 200)
        self.setColumnWidth(1, 50)
        self.setIndentation(20)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.InternalMove)

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

        self.itemClicked.connect(self.on_item_clicked)
        self.itemDoubleClicked.connect(self.on_item_double_clicked)

    def show_context_menu(self, position):
        item = self.itemAt(position)
        if not item:
            return

        menu = QMenu()
        is_group = item.data(0, Qt.UserRole) == "group"
        is_class = item.data(0, Qt.UserRole) == "class"

        if is_group:
            add_class_action = menu.addAction("Добавить подкласс")
            add_class_action.triggered.connect(lambda: self.add_subclass(item))
            rename_action = menu.addAction("Переименовать группу")
            rename_action.triggered.connect(lambda: self.rename_group(item))
            delete_action = menu.addAction("Удалить группу")
            delete_action.triggered.connect(lambda: self.delete_group(item))
        elif is_class:
            change_color_action = menu.addAction("Изменить цвет")
            change_color_action.triggered.connect(lambda: self.change_class_color(item))
            rename_action = menu.addAction("Переименовать класс")
            rename_action.triggered.connect(lambda: self.rename_class(item))
            delete_action = menu.addAction("Удалить класс")
            # Вместо удаления из дерева испускаем сигнал
            delete_action.triggered.connect(lambda: self.delete_class_requested.emit(item.text(0)))

        menu.exec_(self.viewport().mapToGlobal(position))

    def on_item_clicked(self, item, column):
        if item.data(0, Qt.UserRole) == "class":
            class_name = item.text(0)
            self.class_selected.emit(class_name)

    def on_item_double_clicked(self, item, column):
        if item.data(0, Qt.UserRole) == "class":
            class_name = item.text(0)
            self.color_change_requested.emit(class_name)

    def populate_from_hierarchy(self, hierarchy, class_colors, counts=None):
        """Заполняет дерево из иерархии (список).
        hierarchy: список, где каждый элемент может быть строкой (класс) или
                   словарём вида {"name": "группа", "children": [...]}.
        class_colors: словарь {имя_класса: цвет}
        counts: словарь {имя_класса: количество} для отображения счётчиков.
        """
        self.clear()
        self.counts = counts or {}
        self.class_colors = class_colors

        def add_items(parent, items):
            for item_data in items:
                if isinstance(item_data, str):
                    # Это класс
                    self._add_class_item(parent, item_data)
                elif isinstance(item_data, dict) and "name" in item_data:
                    # Это группа
                    group_item = QTreeWidgetItem([item_data["name"], ""])
                    group_item.setData(0, Qt.UserRole, "group")
                    group_item.setFlags(group_item.flags() | Qt.ItemIsEditable)
                    group_item.setIcon(0, QIcon())
                    parent.addChild(group_item)
                    if "children" in item_data:
                        add_items(group_item, item_data["children"])

        root = self.invisibleRootItem()
        add_items(root, hierarchy)
        self.expandAll()

    def _add_class_item(self, parent, class_name):
        """Добавляет элемент класса с иконкой цвета и счётчиком."""
        color = self.class_colors.get(class_name, "#ffffff")
        count = self.counts.get(class_name, 0)
        item = QTreeWidgetItem([class_name, str(count)])
        item.setData(0, Qt.UserRole, "class")
        item.setFlags(item.flags() | Qt.ItemIsDragEnabled)
        pixmap = QPixmap(14, 14)
        pixmap.fill(QColor(color))
        item.setIcon(0, QIcon(pixmap))
        parent.addChild(item)
        return item

    def update_counts(self, counts):
        """Обновляет счётчики в дереве."""
        self.counts = counts
        def update_item(item):
            if item.data(0, Qt.UserRole) == "class":
                class_name = item.text(0)
                count = counts.get(class_name, 0)
                item.setText(1, str(count))
            for i in range(item.childCount()):
                update_item(item.child(i))
        root = self.invisibleRootItem()
        for i in range(root.childCount()):
            update_item(root.child(i))

    def export_to_hierarchy(self):
        """Экспортирует текущее дерево в формат иерархии (список)."""
        hierarchy = []
        root = self.invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            hierarchy.append(self._item_to_dict(item))
        return hierarchy

    def _item_to_dict(self, item):
        if item.data(0, Qt.UserRole) == "class":
            return item.text(0)
        else:
            children = []
            for i in range(item.childCount()):
                children.append(self._item_to_dict(item.child(i)))
            return {"name": item.text(0), "children": children}

    # ----- Методы редактирования через контекстное меню (с сигналами) -----
    def add_subclass(self, group_item):
        class_name, ok = QInputDialog.getText(self, "Новый подкласс", "Введите имя класса:")
        if ok and class_name.strip():
            self._add_class_item(group_item, class_name.strip())
            self.hierarchy_changed.emit()

    def rename_group(self, group_item):
        new_name, ok = QInputDialog.getText(self, "Переименовать группу",
                                            "Новое имя:", text=group_item.text(0))
        if ok and new_name.strip():
            group_item.setText(0, new_name.strip())
            self.hierarchy_changed.emit()

    def rename_class(self, class_item):
        new_name, ok = QInputDialog.getText(self, "Переименовать класс",
                                            "Новое имя:", text=class_item.text(0))
        if ok and new_name.strip():
            class_item.setText(0, new_name.strip())
            self.hierarchy_changed.emit()

    def delete_group(self, group_item):
        reply = QMessageBox.question(self, "Удаление группы",
                                     f"Удалить группу '{group_item.text(0)}' и все её содержимое?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            parent = group_item.parent() or self.invisibleRootItem()
            parent.removeChild(group_item)
            self.hierarchy_changed.emit()

    def delete_class(self, class_item):
        # Этот метод больше не используется для удаления класса через контекстное меню,
        # оставлен для обратной совместимости, но можно удалить.
        pass

    def change_class_color(self, class_item):
        class_name = class_item.text(0)
        self.color_change_requested.emit(class_name)

    def add_group(self, name):
        """Добавляет группу на верхний уровень и возвращает её."""
        item = QTreeWidgetItem([name, ""])
        item.setData(0, Qt.UserRole, "group")
        item.setFlags(item.flags() | Qt.ItemIsEditable)
        self.addTopLevelItem(item)
        self.hierarchy_changed.emit()
        return item