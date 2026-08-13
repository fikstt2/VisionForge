# ui/deduplication_dialog.py
import os
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QMessageBox, QTabWidget, QProgressBar, 
                             QWidget, QCheckBox, QDoubleSpinBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from ui.theme import get_current_theme_style
from core.dataset_deduplicator import DatasetDeduplicator
from core.i18n import tr


class DeduplicationWorker(QThread):
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(dict)

    def __init__(self, images_dir, image_list, sim_thresh, blur_thresh):
        super().__init__()
        self.images_dir = images_dir
        self.image_list = image_list
        self.sim_thresh = sim_thresh
        self.blur_thresh = blur_thresh

    def run(self):
        def on_progress(pct):
            self.progress_signal.emit(pct)

        result = DatasetDeduplicator.analyze_dataset(
            images_dir=self.images_dir,
            image_list=self.image_list,
            similarity_threshold=self.sim_thresh,
            blur_threshold=self.blur_thresh,
            progress_callback=on_progress
        )
        self.finished_signal.emit(result)


class DeduplicationDialog(QDialog):
    def __init__(self, parent=None, project=None):
        super().__init__(parent)
        self.project = project
        self.analysis_results = None
        self.worker = None

        self.setWindowTitle(tr("Поиск дубликатов и контроль качества датасета"))
        self.setMinimumSize(780, 560)
        self.setStyleSheet(get_current_theme_style())

        self.setup_ui()
        self.start_scan()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Верхняя панель настроек сканирования
        top_bar = QHBoxLayout()
        sim_label = QLabel(tr("Порог схожести (%):"))
        self.sim_spin = QDoubleSpinBox()
        self.sim_spin.setRange(70.0, 100.0)
        self.sim_spin.setValue(90.0)
        self.sim_spin.setSingleStep(1.0)

        blur_label = QLabel(tr("Порог резкости (Blur):"))
        self.blur_spin = QDoubleSpinBox()
        self.blur_spin.setRange(10.0, 500.0)
        self.blur_spin.setValue(60.0)
        self.blur_spin.setSingleStep(10.0)

        self.rescan_btn = QPushButton(tr("Пересканировать"))
        self.rescan_btn.clicked.connect(self.start_scan)

        top_bar.addWidget(sim_label)
        top_bar.addWidget(self.sim_spin)
        top_bar.addSpacing(16)
        top_bar.addWidget(blur_label)
        top_bar.addWidget(self.blur_spin)
        top_bar.addStretch()
        top_bar.addWidget(self.rescan_btn)
        layout.addLayout(top_bar)

        # Прогресс-бар
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #18181b;
                border: none;
                border-radius: 3px;
            }
            QProgressBar::chunk {
                background-color: #4f46e5;
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.progress_bar)

        # Вкладки результатов
        self.tabs = QTabWidget()

        # Таб 1: Дубликаты
        self.dupes_tab = QWidget()
        dupes_layout = QVBoxLayout(self.dupes_tab)
        dupes_layout.setContentsMargins(0, 8, 0, 0)

        self.dupes_table = QTableWidget()
        self.dupes_table.setColumnCount(4)
        self.dupes_table.setHorizontalHeaderLabels([
            tr("Выбрать"), tr("Основной кадр"), tr("Похожий / Дубликат"), tr("Схожесть (%)")
        ])
        self.dupes_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.dupes_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.dupes_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.dupes_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        dupes_layout.addWidget(self.dupes_table)

        dupe_actions = QHBoxLayout()
        self.select_all_dupes_btn = QPushButton(tr("Выбрать все дубликаты"))
        self.select_all_dupes_btn.clicked.connect(self.select_all_dupes)
        self.deselect_dupes_btn = QPushButton(tr("Снять выбор"))
        self.deselect_dupes_btn.clicked.connect(self.deselect_all_dupes)
        dupe_actions.addWidget(self.select_all_dupes_btn)
        dupe_actions.addWidget(self.deselect_dupes_btn)
        dupe_actions.addStretch()
        dupes_layout.addLayout(dupe_actions)

        self.tabs.addTab(self.dupes_tab, tr("Дубликаты и серии"))

        # Таб 2: Низкое качество
        self.quality_tab = QWidget()
        q_layout = QVBoxLayout(self.quality_tab)
        q_layout.setContentsMargins(0, 8, 0, 0)

        self.quality_table = QTableWidget()
        self.quality_table.setColumnCount(3)
        self.quality_table.setHorizontalHeaderLabels([
            tr("Выбрать"), tr("Имя файла"), tr("Причина / Оценка")
        ])
        self.quality_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.quality_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.quality_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        q_layout.addWidget(self.quality_table)

        self.tabs.addTab(self.quality_tab, tr("Низкое качество и дефекты"))
        layout.addWidget(self.tabs)

        # Нижние кнопки
        bottom_layout = QHBoxLayout()
        self.delete_btn = QPushButton(tr("Удалить выбранные файлы из проекта"))
        self.delete_btn.setFixedHeight(34)
        self.delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #ef4444;
                color: #ffffff;
                font-weight: bold;
                border-radius: 6px;
                padding: 0 16px;
            }
            QPushButton:hover {
                background-color: #dc2626;
            }
        """)
        self.delete_btn.clicked.connect(self.delete_selected_files)

        self.close_btn = QPushButton(tr("Закрыть"))
        self.close_btn.setFixedHeight(34)
        self.close_btn.clicked.connect(self.accept)

        bottom_layout.addWidget(self.delete_btn)
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.close_btn)
        layout.addLayout(bottom_layout)

    def start_scan(self):
        if not self.project or not self.project.images_list:
            return

        self.rescan_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

        self.worker = DeduplicationWorker(
            images_dir=self.project.images_dir,
            image_list=list(self.project.images_list),
            sim_thresh=self.sim_spin.value(),
            blur_thresh=self.blur_spin.value()
        )
        self.worker.progress_signal.connect(self.progress_bar.setValue)
        self.worker.finished_signal.connect(self.on_scan_finished)
        self.worker.start()

    def on_scan_finished(self, results):
        self.rescan_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.analysis_results = results

        # 1. Заполняем дубликаты
        groups = results.get("duplicate_groups", [])
        total_dupe_rows = sum(len(g["duplicates"]) for g in groups)
        self.dupes_table.setRowCount(total_dupe_rows)

        row = 0
        for g in groups:
            primary_name = g["primary"]
            for d in g["duplicates"]:
                chk = QCheckBox()
                chk.setChecked(True)
                chk.setProperty("filename", d["file"])
                self.dupes_table.setCellWidget(row, 0, chk)

                item_prim = QTableWidgetItem(primary_name)
                item_prim.setFlags(Qt.ItemIsEnabled)
                self.dupes_table.setItem(row, 1, item_prim)

                item_dupe = QTableWidgetItem(d["file"])
                item_dupe.setFlags(Qt.ItemIsEnabled)
                self.dupes_table.setItem(row, 2, item_dupe)

                item_sim = QTableWidgetItem(f"{d['similarity']}%")
                item_sim.setTextAlignment(Qt.AlignCenter)
                item_sim.setFlags(Qt.ItemIsEnabled)
                self.dupes_table.setItem(row, 3, item_sim)
                row += 1

        self.tabs.setTabText(0, f"{tr('Дубликаты и серии')} ({total_dupe_rows})")

        # 2. Заполняем дефекты
        low_q = results.get("low_quality", [])
        self.quality_table.setRowCount(len(low_q))
        for q_row, item in enumerate(low_q):
            chk = QCheckBox()
            chk.setChecked(False)
            chk.setProperty("filename", item["file"])
            self.quality_table.setCellWidget(q_row, 0, chk)

            name_item = QTableWidgetItem(item["file"])
            name_item.setFlags(Qt.ItemIsEnabled)
            self.quality_table.setItem(q_row, 1, name_item)

            reason_item = QTableWidgetItem(item["reason"])
            reason_item.setFlags(Qt.ItemIsEnabled)
            self.quality_table.setItem(q_row, 2, reason_item)

        self.tabs.setTabText(1, f"{tr('Низкое качество и дефекты')} ({len(low_q)})")

    def select_all_dupes(self):
        for r in range(self.dupes_table.rowCount()):
            widget = self.dupes_table.cellWidget(r, 0)
            if isinstance(widget, QCheckBox):
                widget.setChecked(True)

    def deselect_all_dupes(self):
        for r in range(self.dupes_table.rowCount()):
            widget = self.dupes_table.cellWidget(r, 0)
            if isinstance(widget, QCheckBox):
                widget.setChecked(False)

    def delete_selected_files(self):
        files_to_delete = set()

        for r in range(self.dupes_table.rowCount()):
            w = self.dupes_table.cellWidget(r, 0)
            if isinstance(w, QCheckBox) and w.isChecked():
                files_to_delete.add(w.property("filename"))

        for r in range(self.quality_table.rowCount()):
            w = self.quality_table.cellWidget(r, 0)
            if isinstance(w, QCheckBox) and w.isChecked():
                files_to_delete.add(w.property("filename"))

        if not files_to_delete:
            QMessageBox.information(self, tr("Информация"), tr("Не выбрано ни одного файла для удаления."))
            return

        reply = QMessageBox.question(
            self,
            tr("Подтверждение удаления"),
            f"{tr('Вы действительно хотите удалить')} {len(files_to_delete)} {tr('файлов из проекта и с диска?')}",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        deleted_count = 0
        for filename in files_to_delete:
            path = os.path.join(self.project.images_dir, filename)
            try:
                if os.path.exists(path):
                    os.remove(path)
                if filename in self.project.images_list:
                    self.project.images_list.remove(filename)
                if filename in self.project.images_data:
                    del self.project.images_data[filename]
                deleted_count += 1
            except Exception as e:
                print(f"Ошибка удаления {filename}: {e}")

        self.project.save()
        QMessageBox.information(
            self,
            tr("Удаление завершено"),
            f"{tr('Успешно удалено файлов')}: {deleted_count}"
        )
        self.start_scan()
