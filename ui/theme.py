# ui/theme.py
import config
from core.i18n import tr

COMMON_FONT = "font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, 'Inter', Roboto, sans-serif; font-size: 12px;"

# Тёмная тема (Modern Sleek Dark Mode)
DARK_STYLE = f"""
QMainWindow {{
    background-color: #121214;
    {COMMON_FONT}
}}

QMenuBar {{
    background-color: #18181b;
    color: #e4e4e7;
    border-bottom: 1px solid #27272a;
    padding: 2px 4px;
    {COMMON_FONT}
}}
QMenuBar::item {{
    background-color: transparent;
    padding: 6px 12px;
    border-radius: 4px;
    margin: 1px 2px;
}}
QMenuBar::item:selected {{
    background-color: #27272a;
    color: #ffffff;
}}

QMenu {{
    background-color: #1e1e24;
    color: #f4f4f5;
    border: 1px solid #3f3f46;
    border-radius: 8px;
    padding: 6px;
    {COMMON_FONT}
}}
QMenu::item {{
    padding: 7px 28px 7px 14px;
    border-radius: 5px;
    margin: 1px 0px;
}}
QMenu::item:selected {{
    background-color: #4f46e5;
    color: #ffffff;
}}
QMenu::separator {{
    height: 1px;
    background-color: #2e2e36;
    margin: 5px 6px;
}}

QStatusBar {{
    background-color: #18181b;
    color: #a1a1aa;
    border-top: 1px solid #27272a;
    padding: 3px 8px;
    {COMMON_FONT}
}}

QDialog {{
    background-color: #18181b;
    color: #f4f4f5;
    {COMMON_FONT}
}}

QLabel {{
    color: #d4d4d8;
    {COMMON_FONT}
}}

QToolTip {{
    background-color: #27272a;
    color: #f4f4f5;
    border: 1px solid #3f3f46;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 11px;
    {COMMON_FONT}
}}

QGroupBox {{
    color: #f4f4f5;
    border: 1px solid #2e2e38;
    border-radius: 8px;
    margin-top: 14px;
    padding-top: 10px;
    font-weight: 600;
    background-color: #1a1a20;
    {COMMON_FONT}
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 8px;
    color: #a5b4fc;
    font-weight: 600;
}}

QPushButton {{
    background-color: #27272a;
    color: #f4f4f5;
    border: 1px solid #3f3f46;
    border-radius: 6px;
    padding: 6px 14px;
    font-weight: 500;
    {COMMON_FONT}
}}
QPushButton:hover {{
    background-color: #3f3f46;
    border-color: #52525b;
}}
QPushButton:pressed {{
    background-color: #1e1e24;
}}
QPushButton:disabled {{
    background-color: #1f1f23;
    color: #52525b;
    border-color: #27272a;
}}

QPushButton#primary, QPushButton[class="primary"] {{
    background-color: #4f46e5;
    color: #ffffff;
    border: 1px solid #6366f1;
    font-weight: 600;
}}
QPushButton#primary:hover, QPushButton[class="primary"]:hover {{
    background-color: #6366f1;
    border-color: #818cf8;
}}
QPushButton#primary:pressed, QPushButton[class="primary"]:pressed {{
    background-color: #4338ca;
}}

QPushButton#danger, QPushButton[class="danger"] {{
    background-color: #dc2626;
    color: #ffffff;
    border: 1px solid #ef4444;
}}
QPushButton#danger:hover, QPushButton[class="danger"]:hover {{
    background-color: #ef4444;
}}
QPushButton#danger:pressed, QPushButton[class="danger"]:pressed {{
    background-color: #b91c1c;
}}

QPushButton#success, QPushButton[class="success"] {{
    background-color: #16a34a;
    color: #ffffff;
    border: 1px solid #22c55e;
}}
QPushButton#success:hover, QPushButton[class="success"]:hover {{
    background-color: #22c55e;
}}

QPushButton#tool_btn {{
    background-color: #202026;
    color: #d4d4d8;
    border: 1px solid #2d2d38;
    border-radius: 6px;
    font-size: 11px;
    font-weight: 600;
    padding: 4px 6px;
}}
QPushButton#tool_btn:hover {{
    background-color: #2c2c36;
    border-color: #4338ca;
    color: #ffffff;
}}
QPushButton#tool_btn:checked {{
    background-color: #4f46e5;
    border-color: #818cf8;
    color: #ffffff;
}}

QComboBox {{
    background-color: #202026;
    color: #f4f4f5;
    border: 1px solid #383844;
    border-radius: 6px;
    padding: 5px 10px;
    {COMMON_FONT}
}}
QComboBox:hover {{
    border-color: #6366f1;
}}
QComboBox::drop-down {{
    border: none;
    width: 24px;
}}
QComboBox::down-arrow {{
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid #a1a1aa;
    margin-right: 6px;
}}
QComboBox QAbstractItemView {{
    background-color: #1e1e24;
    color: #f4f4f5;
    border: 1px solid #3f3f46;
    border-radius: 6px;
    selection-background-color: #4f46e5;
    selection-color: #ffffff;
    padding: 4px;
    outline: none;
}}

QLineEdit, QSpinBox, QDoubleSpinBox {{
    background-color: #202026;
    color: #f4f4f5;
    border: 1px solid #383844;
    border-radius: 6px;
    padding: 6px 10px;
    {COMMON_FONT}
}}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
    border: 1px solid #818cf8;
    background-color: #24242c;
}}

QCheckBox, QRadioButton {{
    color: #d4d4d8;
    spacing: 8px;
    {COMMON_FONT}
}}
QCheckBox::indicator, QRadioButton::indicator {{
    width: 15px;
    height: 15px;
    border-radius: 4px;
    background-color: #202026;
    border: 1px solid #3f3f46;
}}
QRadioButton::indicator {{
    border-radius: 8px;
}}
QCheckBox::indicator:hover, QRadioButton::indicator:hover {{
    border-color: #818cf8;
}}
QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
    background-color: #4f46e5;
    border-color: #6366f1;
}}

QListWidget, QTreeWidget, QTableWidget {{
    background-color: #18181e;
    color: #f4f4f5;
    border: 1px solid #2e2e38;
    border-radius: 6px;
    padding: 4px;
    outline: none;
    {COMMON_FONT}
}}
QListWidget::item, QTreeWidget::item {{
    padding: 5px 8px;
    border-radius: 5px;
    margin-bottom: 2px;
}}
QListWidget::item:selected, QTreeWidget::item:selected {{
    background-color: #3730a3;
    color: #ffffff;
}}
QListWidget::item:hover:!selected, QTreeWidget::item:hover:!selected {{
    background-color: #24242e;
}}

QProgressBar {{
    border: 1px solid #2e2e38;
    border-radius: 6px;
    text-align: center;
    background-color: #18181e;
    color: #f4f4f5;
    font-weight: 600;
    font-size: 11px;
    {COMMON_FONT}
}}
QProgressBar::chunk {{
    background-color: #4f46e5;
    border-radius: 5px;
}}

QTabWidget::pane {{
    border: 1px solid #2e2e38;
    border-radius: 8px;
    background-color: #18181e;
    top: -1px;
}}
QTabBar::tab {{
    background-color: #202026;
    color: #a1a1aa;
    border: 1px solid #2e2e38;
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    padding: 8px 18px;
    margin-right: 4px;
    font-weight: 500;
    {COMMON_FONT}
}}
QTabBar::tab:selected {{
    background-color: #18181e;
    color: #ffffff;
    border-bottom: 2px solid #6366f1;
    font-weight: 600;
}}
QTabBar::tab:hover:!selected {{
    background-color: #272730;
    color: #d4d4d8;
}}

QScrollBar:vertical {{
    border: none;
    background-color: transparent;
    width: 8px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background-color: #383844;
    border-radius: 4px;
    min-height: 24px;
}}
QScrollBar::handle:vertical:hover {{
    background-color: #52525e;
}}
QScrollBar:horizontal {{
    border: none;
    background-color: transparent;
    height: 8px;
    margin: 0;
}}
QScrollBar::handle:horizontal {{
    background-color: #383844;
    border-radius: 4px;
    min-width: 24px;
}}
QScrollBar::handle:horizontal:hover {{
    background-color: #52525e;
}}

QHeaderView::section {{
    background-color: #15151a;
    color: #a1a1aa;
    border: none;
    border-bottom: 1px solid #2e2e38;
    padding: 7px 10px;
    font-weight: 600;
    {COMMON_FONT}
}}

QSplitter::handle {{
    background-color: #27272f;
}}
QSplitter::handle:hover {{
    background-color: #6366f1;
}}
"""

# Светлая тема (Light Clean Crisp Mode)
LIGHT_STYLE = f"""
QMainWindow {{
    background-color: #f8fafc;
    {COMMON_FONT}
}}

QMenuBar {{
    background-color: #ffffff;
    color: #0f172a;
    border-bottom: 1px solid #e2e8f0;
    padding: 2px 4px;
    {COMMON_FONT}
}}
QMenuBar::item {{
    background-color: transparent;
    padding: 6px 12px;
    border-radius: 4px;
    margin: 1px 2px;
}}
QMenuBar::item:selected {{
    background-color: #f1f5f9;
    color: #0f172a;
}}

QMenu {{
    background-color: #ffffff;
    color: #0f172a;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    padding: 6px;
    {COMMON_FONT}
}}
QMenu::item {{
    padding: 7px 28px 7px 14px;
    border-radius: 5px;
    margin: 1px 0px;
}}
QMenu::item:selected {{
    background-color: #2563eb;
    color: #ffffff;
}}
QMenu::separator {{
    height: 1px;
    background-color: #e2e8f0;
    margin: 5px 6px;
}}

QStatusBar {{
    background-color: #ffffff;
    color: #64748b;
    border-top: 1px solid #e2e8f0;
    padding: 3px 8px;
    {COMMON_FONT}
}}

QDialog {{
    background-color: #ffffff;
    color: #0f172a;
    {COMMON_FONT}
}}

QLabel {{
    color: #334155;
    {COMMON_FONT}
}}

QToolTip {{
    background-color: #0f172a;
    color: #ffffff;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 11px;
    {COMMON_FONT}
}}

QGroupBox {{
    color: #0f172a;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    margin-top: 14px;
    padding-top: 10px;
    font-weight: 600;
    background-color: #ffffff;
    {COMMON_FONT}
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 8px;
    color: #2563eb;
    font-weight: 600;
}}

QPushButton {{
    background-color: #ffffff;
    color: #0f172a;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 6px 14px;
    font-weight: 500;
    {COMMON_FONT}
}}
QPushButton:hover {{
    background-color: #f1f5f9;
    border-color: #94a3b8;
}}
QPushButton:pressed {{
    background-color: #e2e8f0;
}}
QPushButton:disabled {{
    background-color: #f8fafc;
    color: #94a3b8;
    border-color: #e2e8f0;
}}

QPushButton#primary, QPushButton[class="primary"] {{
    background-color: #2563eb;
    color: #ffffff;
    border: 1px solid #1d4ed8;
    font-weight: 600;
}}
QPushButton#primary:hover, QPushButton[class="primary"]:hover {{
    background-color: #1d4ed8;
}}

QPushButton#danger, QPushButton[class="danger"] {{
    background-color: #dc2626;
    color: #ffffff;
    border: 1px solid #b91c1c;
}}
QPushButton#danger:hover, QPushButton[class="danger"]:hover {{
    background-color: #b91c1c;
}}

QPushButton#tool_btn {{
    background-color: #ffffff;
    color: #334155;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    font-size: 11px;
    font-weight: 600;
    padding: 4px 6px;
}}
QPushButton#tool_btn:hover {{
    background-color: #eff6ff;
    border-color: #2563eb;
    color: #1d4ed8;
}}
QPushButton#tool_btn:checked {{
    background-color: #2563eb;
    border-color: #1d4ed8;
    color: #ffffff;
}}

QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox {{
    background-color: #ffffff;
    color: #0f172a;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 6px 10px;
    {COMMON_FONT}
}}
QComboBox:hover, QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
    border: 1px solid #2563eb;
}}

QCheckBox, QRadioButton {{
    color: #334155;
    spacing: 8px;
    {COMMON_FONT}
}}
QCheckBox::indicator, QRadioButton::indicator {{
    width: 15px;
    height: 15px;
    border-radius: 4px;
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
}}
QRadioButton::indicator {{
    border-radius: 8px;
}}
QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
    background-color: #2563eb;
    border-color: #1d4ed8;
}}

QListWidget, QTreeWidget, QTableWidget {{
    background-color: #ffffff;
    color: #0f172a;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    padding: 4px;
    outline: none;
    {COMMON_FONT}
}}
QListWidget::item, QTreeWidget::item {{
    padding: 5px 8px;
    border-radius: 5px;
    margin-bottom: 2px;
}}
QListWidget::item:selected, QTreeWidget::item:selected {{
    background-color: #eff6ff;
    color: #1d4ed8;
    font-weight: 600;
}}
QListWidget::item:hover:!selected, QTreeWidget::item:hover:!selected {{
    background-color: #f8fafc;
}}

QProgressBar {{
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    text-align: center;
    background-color: #f1f5f9;
    color: #0f172a;
    font-weight: 600;
    font-size: 11px;
    {COMMON_FONT}
}}
QProgressBar::chunk {{
    background-color: #2563eb;
    border-radius: 5px;
}}

QTabWidget::pane {{
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    background-color: #ffffff;
    top: -1px;
}}
QTabBar::tab {{
    background-color: #f1f5f9;
    color: #64748b;
    border: 1px solid #cbd5e1;
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    padding: 8px 18px;
    margin-right: 4px;
    font-weight: 500;
    {COMMON_FONT}
}}
QTabBar::tab:selected {{
    background-color: #ffffff;
    color: #0f172a;
    border-bottom: 2px solid #2563eb;
    font-weight: 600;
}}

QScrollBar:vertical, QScrollBar:horizontal {{
    border: none;
    background-color: transparent;
    width: 8px;
    height: 8px;
}}
QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{
    background-color: #cbd5e1;
    border-radius: 4px;
}}
QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {{
    background-color: #94a3b8;
}}

QHeaderView::section {{
    background-color: #f8fafc;
    color: #64748b;
    border: none;
    border-bottom: 1px solid #e2e8f0;
    padding: 7px 10px;
    font-weight: 600;
    {COMMON_FONT}
}}

QSplitter::handle {{
    background-color: #e2e8f0;
}}
QSplitter::handle:hover {{
    background-color: #2563eb;
}}
"""

# Высококонтрастная тема
HIGH_CONTRAST_STYLE = f"""
QMainWindow {{
    background-color: #000000;
    {COMMON_FONT}
}}
QMenuBar {{
    background-color: #000000;
    color: #ffffff;
    border-bottom: 2px solid #ffff00;
    {COMMON_FONT}
}}
QMenuBar::item:selected {{
    background-color: #ffff00;
    color: #000000;
}}
QMenu {{
    background-color: #000000;
    color: #ffffff;
    border: 2px solid #ffffff;
    {COMMON_FONT}
}}
QMenu::item:selected {{
    background-color: #ffff00;
    color: #000000;
}}
QStatusBar {{
    background-color: #000000;
    color: #ffffff;
    border-top: 2px solid #ffff00;
    {COMMON_FONT}
}}
QDialog {{
    background-color: #000000;
    color: #ffffff;
    {COMMON_FONT}
}}
QLabel {{
    color: #ffffff;
    font-weight: bold;
    {COMMON_FONT}
}}
QGroupBox {{
    color: #ffffff;
    border: 2px solid #ffff00;
    border-radius: 6px;
    margin-top: 14px;
    font-weight: bold;
    background-color: #000000;
    {COMMON_FONT}
}}
QGroupBox::title {{
    left: 10px;
    padding: 0 6px;
    color: #ffff00;
}}
QPushButton {{
    background-color: #000000;
    color: #ffffff;
    border: 2px solid #ffffff;
    border-radius: 6px;
    padding: 6px 14px;
    font-weight: bold;
    {COMMON_FONT}
}}
QPushButton:hover {{
    background-color: #ffff00;
    color: #000000;
}}
QPushButton#tool_btn:checked {{
    background-color: #ffff00;
    color: #000000;
}}
QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox {{
    background-color: #000000;
    color: #ffffff;
    border: 2px solid #ffffff;
    border-radius: 6px;
    padding: 6px;
    {COMMON_FONT}
}}
QListWidget, QTreeWidget, QTableWidget {{
    background-color: #000000;
    color: #ffffff;
    border: 2px solid #ffffff;
    border-radius: 6px;
    padding: 4px;
    {COMMON_FONT}
}}
QListWidget::item:selected, QTreeWidget::item:selected {{
    background-color: #ffff00;
    color: #000000;
}}
QProgressBar {{
    border: 2px solid #ffffff;
    border-radius: 6px;
    background-color: #000000;
    color: #ffffff;
    font-weight: bold;
    {COMMON_FONT}
}}
QProgressBar::chunk {{
    background-color: #ffff00;
}}
QTabBar::tab {{
    background-color: #000000;
    color: #ffffff;
    border: 2px solid #ffffff;
    padding: 6px 16px;
    {COMMON_FONT}
}}
QTabBar::tab:selected {{
    background-color: #ffff00;
    color: #000000;
}}
"""

THEMES = {
    tr("Тёмная"): DARK_STYLE,
    tr("Светлая"): LIGHT_STYLE,
    tr("Высококонтрастная"): HIGH_CONTRAST_STYLE,
}

def get_theme(name):
    return THEMES.get(name, DARK_STYLE)
    
def get_current_theme_style():
    cfg = config.load_config()
    return get_theme(cfg.get("theme", "Тёмная"))