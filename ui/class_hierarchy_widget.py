# ui/class_hierarchy_widget.py
from PyQt5.QtWidgets import (QTreeWidget, QTreeWidgetItem, QMenu, QInputDialog,
                             QMessageBox, QColorDialog, QAbstractItemView)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QIcon, QPixmap
from core.i18n import tr

class ClassHierarchyWidget(QTreeWidget):
    """Дерево для отображения и редактирования иерархии классов."""
    class_selected = pyqtSignal(str)          # имя класса (не группы)
    color_change_requested = pyqtSignal(str)  # имя класса
    hierarchy_changed = pyqtSignal()          # структура изменилась (переименование, перемещение)
    delete_class_requested = pyqtSignal(str)  # запрос на удаление класса

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderLabels([tr("Класс / Группа"), tr("Счётчик")])
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
        # Connect checkbox state changes
        self.itemChanged.connect(self.on_item_changed)

    def show_context_menu(self, position):
        item = self.itemAt(position)
        if not item:
            return

        menu = QMenu()
        is_group = item.data(0, Qt.UserRole) == "group"
        is_class = item.data(0, Qt.UserRole) == "class"

        if is_group:
            add_class_action = menu.addAction(tr("Добавить подкласс"))
            add_class_action.triggered.connect(lambda: self.add_subclass(item))
            rename_action = menu.addAction(tr("Переименовать группу"))
            rename_action.triggered.connect(lambda: self.rename_group(item))
            delete_action = menu.addAction(tr("Удалить группу"))
            delete_action.triggered.connect(lambda: self.delete_group(item))
        elif is_class:
            change_color_action = menu.addAction(tr("Изменить цвет"))
            change_color_action.triggered.connect(lambda: self.change_class_color(item))
            rename_action = menu.addAction(tr("Переименовать класс"))
            rename_action.triggered.connect(lambda: self.rename_class(item))
            delete_action = menu.addAction(tr("Удалить класс"))
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
        self.blockSignals(True)
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
                    group_item.setFlags(group_item.flags() | Qt.ItemIsEditable | Qt.ItemIsUserCheckable)
                    group_item.setCheckState(0, Qt.Checked)
                    group_item.setIcon(0, QIcon())
                    parent.addChild(group_item)
                    if "children" in item_data:
                        add_items(group_item, item_data["children"])

        root = self.invisibleRootItem()
        add_items(root, hierarchy)
        self.expandAll()
        self.blockSignals(False)

    def _add_class_item(self, parent, class_name):
        """Добавляет элемент класса с иконкой цвета и счётчиком."""
        color = self.class_colors.get(class_name, "#ffffff")
        count = self.counts.get(class_name, 0)
        item = QTreeWidgetItem([class_name, str(count)])
        item.setData(0, Qt.UserRole, "class")
        item.setFlags(item.flags() | Qt.ItemIsDragEnabled | Qt.ItemIsUserCheckable)
        item.setCheckState(0, Qt.Checked)
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
        class_name, ok = QInputDialog.getText(self, tr("Новый подкласс"), tr("Введите имя класса:"))
        if ok and class_name.strip():
            self._add_class_item(group_item, class_name.strip())
            self.hierarchy_changed.emit()

    def rename_group(self, group_item):
        new_name, ok = QInputDialog.getText(self, tr("Переименовать группу"),
                                            tr("Новое имя:"), text=group_item.text(0))
        if ok and new_name.strip():
            group_item.setText(0, new_name.strip())
            self.hierarchy_changed.emit()

    def rename_class(self, class_item):
        new_name, ok = QInputDialog.getText(self, tr("Переименовать класс"),
                                            tr("Новое имя:"), text=class_item.text(0))
        if ok and new_name.strip():
            class_item.setText(0, new_name.strip())
            self.hierarchy_changed.emit()

    def on_item_changed(self, item, column):
        """Propagate check state to children and update parents."""
        if column != 0:
            return
        state = item.checkState(0)
        
        self.blockSignals(True)
        # Apply to all children recursively
        def set_children_check(it):
            for i in range(it.childCount()):
                child = it.child(i)
                child.setCheckState(0, state)
                set_children_check(child)
        set_children_check(item)
        
        # Update parent based on siblings
        def update_parent(it):
            parent = it.parent()
            if parent is None:
                return
            # If any child is checked, parent should be partially checked (Qt.PartiallyChecked) or checked if all
            checked = 0
            unchecked = 0
            for i in range(parent.childCount()):
                cs = parent.child(i).checkState(0)
                if cs == Qt.Checked:
                    checked += 1
                elif cs == Qt.Unchecked:
                    unchecked += 1
            
            if checked == parent.childCount():
                parent.setCheckState(0, Qt.Checked)
            elif unchecked == parent.childCount():
                parent.setCheckState(0, Qt.Unchecked)
            else:
                parent.setCheckState(0, Qt.PartiallyChecked)
            update_parent(parent)
        
        update_parent(item)
        self.blockSignals(False)

    def get_mapping(self, merge_to_parent=True):
        """Return mapping of each checked class to its top‑level group name if merge_to_parent is True.
        If merge_to_parent is False, maps each class to itself.
        If a class has no group ancestors, it maps to itself.
        """
        mapping = {}
        def traverse(item, top_group=None):
            for i in range(item.childCount()):
                child = item.child(i)
                role = child.data(0, Qt.UserRole)
                if role == "group":
                    # This group becomes the new top_group for its descendants
                    traverse(child, child.text(0))
                elif role == "class":
                    if child.checkState(0) == Qt.Checked:
                        if merge_to_parent:
                            mapping[child.text(0)] = top_group if top_group else child.text(0)
                        else:
                            mapping[child.text(0)] = child.text(0)
        root = self.invisibleRootItem()
        traverse(root)
        return mapping

    def get_excluded_classes(self):
        """Return set of class names that are unchecked (excluded)."""
        excluded = set()
        def collect(item):
            for i in range(item.childCount()):
                child = item.child(i)
                role = child.data(0, Qt.UserRole)
                if role == "class" and child.checkState(0) == Qt.Unchecked:
                    excluded.add(child.text(0))
                collect(child)
        collect(self.invisibleRootItem())
        return excluded

    def delete_group(self, group_item):
        reply = QMessageBox.question(self, tr("Удаление группы"),
                                     f"{tr('Удалить группу')} '{group_item.text(0)}' {tr('и все её содержимое?')}",
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
        # make group checkable and initially checked
        item.setFlags(item.flags() | Qt.ItemIsEditable | Qt.ItemIsUserCheckable)
        item.setCheckState(0, Qt.Checked)
        self.addTopLevelItem(item)
        self.hierarchy_changed.emit()
        return item