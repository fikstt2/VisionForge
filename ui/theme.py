# ui/theme.py
import config

# Тёмная тема (по умолчанию)
DARK_STYLE = """
QMainWindow {
    background-color: #1e1e1e;
}
QMenuBar {
    background-color: #252525;
    color: #ffffff;
    border-bottom: 1px solid #3c3c3c;
}
QMenuBar::item {
    background-color: transparent;
    padding: 4px 10px;
    margin: 0px;
}
QMenuBar::item:selected {
    background-color: #0d7377;
    border-radius: 4px;
}
QMenu {
    background-color: #2b2b2b;
    color: #ffffff;
    border: 1px solid #3c3c3c;
    border-radius: 6px;
    padding: 4px;
}
QMenu::item {
    padding: 6px 24px;
    border-radius: 4px;
}
QMenu::item:selected {
    background-color: #0d7377;
}
QMenu::separator {
    height: 1px;
    background-color: #3c3c3c;
    margin: 6px 4px;
}
QStatusBar {
    background-color: #252525;
    color: #dddddd;
    border-top: 1px solid #3c3c3c;
}
QDialog {
    background-color: #2b2b2b;
    color: #ffffff;
}
QLabel {
    color: #dddddd;
    font-size: 10px;
}
QGroupBox {
    color: #ffffff;
    border: 1px solid #3c3c3c;
    border-radius: 6px;
    margin-top: 8px;
    font-weight: bold;
    background-color: #2b2b2b;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px 0 4px;
    color: #0d7377;
    font-size: 10px;
    font-weight: bold;
}
QPushButton {
    background-color: #0d7377;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 2px 4px;
    font-size: 10px;
    font-weight: normal;
}
QPushButton:hover {
    background-color: #14a085;
}
QPushButton:pressed {
    background-color: #0b5e5e;
}
QPushButton#danger {
    background-color: #c0392b;
}
QPushButton#danger:hover {
    background-color: #e74c3c;
}
QPushButton#success {
    background-color: #27ae60;
}
QPushButton#success:hover {
    background-color: #2ecc71;
}
QComboBox {
    background-color: #3c3c3c;
    color: #ffffff;
    border: 1px solid #555555;
    border-radius: 4px;
    padding: 2px;
    font-size: 10px;
}
QComboBox::drop-down {
    border: none;
    width: 16px;
}
QComboBox::down-arrow {
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 4px solid #ffffff;
    margin-right: 4px;
}
QComboBox QAbstractItemView {
    background-color: #3c3c3c;
    color: #ffffff;
    border: 1px solid #555555;
    selection-background-color: #0d7377;
}
QLineEdit {
    background-color: #3c3c3c;
    color: #ffffff;
    border: 1px solid #555555;
    border-radius: 4px;
    padding: 4px;
    font-size: 10px;
}
QSpinBox, QDoubleSpinBox {
    background-color: #3c3c3c;
    color: #ffffff;
    border: 1px solid #555555;
    border-radius: 4px;
    padding: 2px;
    font-size: 10px;
}
QCheckBox {
    color: #dddddd;
    spacing: 4px;
    font-size: 10px;
}
QCheckBox::indicator {
    width: 12px;
    height: 12px;
    border-radius: 2px;
    background-color: #3c3c3c;
    border: 1px solid #555555;
}
QCheckBox::indicator:checked {
    background-color: #0d7377;
    border-color: #0d7377;
    image: url(data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxMiIgaGVpZ2h0PSIxMiIgdmlld0JveD0iMCAwIDEyIDEyIj48cGF0aCBkPSJNOS41IDMuNUw1IDggMi41IDUuNSIgc3Ryb2tlPSIjZmZmZmZmIiBzdHJva2Utd2lkdGg9IjIiIGZpbGw9Im5vbmUiLz48L3N2Zz4=);
}
QListWidget {
    background-color: #3c3c3c;
    color: #ffffff;
    border: 1px solid #555555;
    border-radius: 4px;
    padding: 2px;
    font-size: 10px;
    outline: none;
}
QListWidget::item {
    padding: 2px;
    border-radius: 2px;
}
QListWidget::item:selected {
    background-color: #0d7377;
}
QListWidget::item:hover {
    background-color: #4a4a4a;
}
QProgressBar {
    border: 1px solid #3c3c3c;
    border-radius: 4px;
    text-align: center;
    background-color: #2b2b2b;
    color: #ffffff;
    font-weight: normal;
    font-size: 10px;
}
QProgressBar::chunk {
    background-color: #0d7377;
    border-radius: 4px;
}
QTabWidget::pane {
    border: 1px solid #3c3c3c;
    border-radius: 4px;
    background-color: #2b2b2b;
}
QTabBar::tab {
    background-color: #3c3c3c;
    color: #dddddd;
    border: 1px solid #3c3c3c;
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    padding: 4px 6px;
    margin-right: 2px;
    font-size: 10px;
}
QTabBar::tab:selected {
    background-color: #0d7377;
    color: #ffffff;
}
QTabBar::tab:hover:!selected {
    background-color: #4a4a4a;
}
QScrollBar:vertical {
    border: none;
    background-color: #2b2b2b;
    width: 8px;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background-color: #4a4a4a;
    border-radius: 4px;
    min-height: 20px;
}
QScrollBar::handle:vertical:hover {
    background-color: #5a5a5a;
}
QScrollBar:horizontal {
    border: none;
    background-color: #2b2b2b;
    height: 8px;
    border-radius: 4px;
}
QScrollBar::handle:horizontal {
    background-color: #4a4a4a;
    border-radius: 4px;
    min-width: 20px;
}
QScrollBar::handle:horizontal:hover {
    background-color: #5a5a5a;
}
QScrollBar::add-line, QScrollBar::sub-line {
    border: none;
    background: none;
}
QDialogButtonBox QPushButton {
    min-width: 80px;
}
QTreeWidget {
    background-color: #3c3c3c;
    color: #ffffff;
    border: 1px solid #555555;
    border-radius: 4px;
    padding: 2px;
    font-size: 10px;
    outline: none;
}
QTreeWidget::item {
    padding: 2px;
    border-radius: 2px;
}
QTreeWidget::item:selected {
    background-color: #0d7377;
}
QTreeWidget::item:hover {
    background-color: #4a4a4a;
}
QHeaderView::section {
    background-color: #2b2b2b;
    color: #dddddd;
    border: 1px solid #3c3c3c;
    padding: 2px;
    font-size: 10px;
}
QTextEdit, QPlainTextEdit {
    background-color: #3c3c3c;
    color: #ffffff;
    border: 1px solid #555555;
    border-radius: 4px;
    padding: 4px;
    font-size: 10px;
    selection-background-color: #0d7377;
}
QTableWidget {
    background-color: #3c3c3c;
    color: #ffffff;
    border: 1px solid #555555;
    gridline-color: #555555;
    selection-background-color: #0d7377;
}
QTableWidget::item {
    padding: 2px;
}
QTableWidget QHeaderView::section {
    background-color: #2b2b2b;
    color: #dddddd;
    border: 1px solid #3c3c3c;
    padding: 4px;
    font-size: 10px;
}
"""

LIGHT_STYLE = """
QMainWindow {
    background-color: #f0f0f0;
}
QMenuBar {
    background-color: #e0e0e0;
    color: #000000;
    border-bottom: 1px solid #c0c0c0;
}
QMenuBar::item:selected {
    background-color: #0d7377;
    color: #ffffff;
}
QMenu {
    background-color: #ffffff;
    color: #000000;
    border: 1px solid #c0c0c0;
}
QMenu::item:selected {
    background-color: #0d7377;
    color: #ffffff;
}
QStatusBar {
    background-color: #e0e0e0;
    color: #000000;
    border-top: 1px solid #c0c0c0;
}
QDialog {
    background-color: #f0f0f0;
    color: #000000;
}
QLabel {
    color: #000000;
    font-size: 10px;
}
QGroupBox {
    color: #000000;
    border: 1px solid #c0c0c0;
    border-radius: 6px;
    margin-top: 8px;
    font-weight: bold;
    background-color: #ffffff;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px 0 4px;
    color: #0d7377;
    font-size: 10px;
    font-weight: bold;
}
QPushButton {
    background-color: #e0e0e0;
    color: #000000;
    border: 1px solid #a0a0a0;
    border-radius: 4px;
    padding: 2px 4px;
    font-size: 10px;
}
QPushButton:hover {
    background-color: #d0d0d0;
}
QPushButton:pressed {
    background-color: #c0c0c0;
}
QPushButton#danger {
    background-color: #ffcccc;
    color: #a00000;
}
QComboBox {
    background-color: #ffffff;
    color: #000000;
    border: 1px solid #a0a0a0;
    border-radius: 4px;
    padding: 2px;
    font-size: 10px;
}
QComboBox::drop-down {
    border: none;
    width: 16px;
}
QComboBox::down-arrow {
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 4px solid #000000;
    margin-right: 4px;
}
QComboBox QAbstractItemView {
    background-color: #ffffff;
    color: #000000;
    border: 1px solid #a0a0a0;
    selection-background-color: #0d7377;
    selection-color: #ffffff;
}
QLineEdit {
    background-color: #ffffff;
    color: #000000;
    border: 1px solid #a0a0a0;
    border-radius: 4px;
    padding: 4px;
    font-size: 10px;
}
QSpinBox, QDoubleSpinBox {
    background-color: #ffffff;
    color: #000000;
    border: 1px solid #a0a0a0;
    border-radius: 4px;
    padding: 2px;
    font-size: 10px;
}
QRadioButton, QCheckBox {
    color: #000000;
    spacing: 4px;
    font-size: 10px;
}
QRadioButton::indicator, QCheckBox::indicator {
    width: 12px;
    height: 12px;
    border-radius: 2px;
    background-color: #ffffff;
    border: 1px solid #a0a0a0;
}
QRadioButton::indicator:checked, QCheckBox::indicator:checked {
    background-color: #0d7377;
    border-color: #0d7377;
}
QListWidget {
    background-color: #ffffff;
    color: #000000;
    border: 1px solid #a0a0a0;
    border-radius: 4px;
    padding: 2px;
    font-size: 10px;
}
QListWidget::item:selected {
    background-color: #0d7377;
    color: #ffffff;
}
QListWidget::item:hover {
    background-color: #e0e0e0;
}
QProgressBar {
    border: 1px solid #a0a0a0;
    border-radius: 4px;
    text-align: center;
    background-color: #ffffff;
    color: #000000;
    font-size: 10px;
}
QProgressBar::chunk {
    background-color: #0d7377;
    border-radius: 4px;
}
QTabWidget::pane {
    border: 1px solid #a0a0a0;
    border-radius: 4px;
    background-color: #ffffff;
}
QTabBar::tab {
    background-color: #e0e0e0;
    color: #000000;
    border: 1px solid #a0a0a0;
    border-bottom: none;
    padding: 4px 6px;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background-color: #ffffff;
}
QScrollBar:vertical {
    border: none;
    background-color: #e0e0e0;
    width: 8px;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background-color: #a0a0a0;
    border-radius: 4px;
    min-height: 20px;
}
QScrollBar:horizontal {
    border: none;
    background-color: #e0e0e0;
    height: 8px;
    border-radius: 4px;
}
QScrollBar::handle:horizontal {
    background-color: #a0a0a0;
    border-radius: 4px;
    min-width: 20px;
}
QDialogButtonBox QPushButton {
    min-width: 80px;
}
QTreeWidget {
    background-color: #ffffff;
    color: #000000;
    border: 1px solid #a0a0a0;
    border-radius: 4px;
    padding: 2px;
    font-size: 10px;
}
QTreeWidget::item:selected {
    background-color: #0d7377;
    color: #ffffff;
}
QHeaderView::section {
    background-color: #e0e0e0;
    color: #000000;
    border: 1px solid #a0a0a0;
    padding: 2px;
    font-size: 10px;
}
QTextEdit, QPlainTextEdit {
    background-color: #ffffff;
    color: #000000;
    border: 1px solid #a0a0a0;
    border-radius: 4px;
    padding: 4px;
    font-size: 10px;
    selection-background-color: #0d7377;
    selection-color: #ffffff;
}
QTableWidget {
    background-color: #ffffff;
    color: #000000;
    border: 1px solid #a0a0a0;
    gridline-color: #a0a0a0;
    selection-background-color: #0d7377;
    selection-color: #ffffff;
}
QTableWidget::item {
    padding: 2px;
}
QTableWidget QHeaderView::section {
    background-color: #e0e0e0;
    color: #000000;
    border: 1px solid #a0a0a0;
    padding: 4px;
    font-size: 10px;
}
"""

# Высококонтрастная тема (добавлены QRadioButton, QCheckBox)
HIGH_CONTRAST_STYLE = """
QMainWindow {
    background-color: #000000;
}
QMenuBar {
    background-color: #000000;
    color: #ffffff;
    border-bottom: 2px solid #ffff00;
}
QMenuBar::item:selected {
    background-color: #ffff00;
    color: #000000;
}
QMenu {
    background-color: #000000;
    color: #ffffff;
    border: 2px solid #ffffff;
}
QMenu::item:selected {
    background-color: #ffff00;
    color: #000000;
}
QStatusBar {
    background-color: #000000;
    color: #ffffff;
    border-top: 2px solid #ffff00;
}
QDialog {
    background-color: #000000;
    color: #ffffff;
}
QLabel {
    color: #ffffff;
    font-size: 10px;
}
QGroupBox {
    color: #ffffff;
    border: 2px solid #ffff00;
    border-radius: 6px;
    margin-top: 8px;
    font-weight: bold;
    background-color: #000000;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px 0 4px;
    color: #ffff00;
    font-size: 10px;
    font-weight: bold;
}
QPushButton {
    background-color: #000000;
    color: #ffffff;
    border: 2px solid #ffffff;
    border-radius: 4px;
    padding: 2px 4px;
    font-size: 10px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #ffff00;
    color: #000000;
}
QPushButton:pressed {
    background-color: #00ff00;
    color: #000000;
}
QPushButton#danger {
    background-color: #ff0000;
    color: #ffffff;
}
QComboBox {
    background-color: #000000;
    color: #ffffff;
    border: 2px solid #ffffff;
    border-radius: 4px;
    padding: 2px;
    font-size: 10px;
}
QComboBox::drop-down {
    border: none;
    width: 16px;
}
QComboBox::down-arrow {
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 4px solid #ffffff;
    margin-right: 4px;
}
QComboBox QAbstractItemView {
    background-color: #000000;
    color: #ffffff;
    border: 2px solid #ffffff;
    selection-background-color: #ffff00;
    selection-color: #000000;
}
QLineEdit {
    background-color: #000000;
    color: #ffffff;
    border: 2px solid #ffffff;
    border-radius: 4px;
    padding: 4px;
    font-size: 10px;
}
QSpinBox, QDoubleSpinBox {
    background-color: #000000;
    color: #ffffff;
    border: 2px solid #ffffff;
    border-radius: 4px;
    padding: 2px;
    font-size: 10px;
}
QRadioButton, QCheckBox {
    color: #ffffff;
    spacing: 4px;
    font-size: 10px;
}
QRadioButton::indicator, QCheckBox::indicator {
    width: 12px;
    height: 12px;
    border-radius: 2px;
    background-color: #000000;
    border: 2px solid #ffffff;
}
QRadioButton::indicator:checked, QCheckBox::indicator:checked {
    background-color: #ffff00;
    border-color: #ffff00;
}
QListWidget {
    background-color: #000000;
    color: #ffffff;
    border: 2px solid #ffffff;
    border-radius: 4px;
    padding: 2px;
    font-size: 10px;
}
QListWidget::item:selected {
    background-color: #ffff00;
    color: #000000;
}
QListWidget::item:hover {
    background-color: #00ff00;
    color: #000000;
}
QProgressBar {
    border: 2px solid #ffffff;
    border-radius: 4px;
    text-align: center;
    background-color: #000000;
    color: #ffffff;
    font-size: 10px;
}
QProgressBar::chunk {
    background-color: #ffff00;
    border-radius: 4px;
}
QTabWidget::pane {
    border: 2px solid #ffffff;
    border-radius: 4px;
    background-color: #000000;
}
QTabBar::tab {
    background-color: #000000;
    color: #ffffff;
    border: 2px solid #ffffff;
    border-bottom: none;
    padding: 4px 6px;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background-color: #ffff00;
    color: #000000;
}
QScrollBar:vertical {
    border: 2px solid #ffffff;
    background-color: #000000;
    width: 10px;
    border-radius: 5px;
}
QScrollBar::handle:vertical {
    background-color: #ffff00;
    border-radius: 4px;
    min-height: 20px;
}
QScrollBar:horizontal {
    border: 2px solid #ffffff;
    background-color: #000000;
    height: 10px;
    border-radius: 5px;
}
QScrollBar::handle:horizontal {
    background-color: #ffff00;
    border-radius: 4px;
    min-width: 20px;
}
QDialogButtonBox QPushButton {
    min-width: 80px;
}
QTreeWidget {
    background-color: #000000;
    color: #ffffff;
    border: 2px solid #ffffff;
    border-radius: 4px;
    padding: 2px;
    font-size: 10px;
}
QTreeWidget::item:selected {
    background-color: #ffff00;
    color: #000000;
}
QHeaderView::section {
    background-color: #000000;
    color: #ffffff;
    border: 2px solid #ffffff;
    padding: 2px;
    font-size: 10px;
}
QTextEdit, QPlainTextEdit {
    background-color: #000000;
    color: #ffffff;
    border: 2px solid #ffffff;
    border-radius: 4px;
    padding: 4px;
    font-size: 10px;
    selection-background-color: #ffff00;
    selection-color: #000000;
}
QTableWidget {
    background-color: #000000;
    color: #ffffff;
    border: 2px solid #ffffff;
    gridline-color: #ffffff;
    selection-background-color: #ffff00;
    selection-color: #000000;
}
QTableWidget::item {
    padding: 2px;
}
QTableWidget QHeaderView::section {
    background-color: #000000;
    color: #ffffff;
    border: 2px solid #ffffff;
    padding: 4px;
    font-size: 10px;
}
"""

THEMES = {
    "Тёмная": DARK_STYLE,
    "Светлая": LIGHT_STYLE,
    "Высококонтрастная": HIGH_CONTRAST_STYLE,
}

def get_theme(name):
    return THEMES.get(name, DARK_STYLE)

def get_current_theme_style():
    return get_theme(config.THEME)