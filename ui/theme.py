# ui/theme.py
import config
from core.i18n import tr

COMMON_FONT = "font-family: 'Segoe UI', 'Inter', 'Roboto', sans-serif; font-size: 12px;"

# Тёмная тема (Modern Sleek Dark Mode)
DARK_STYLE = f"""
QMainWindow {{ background-color: #18181b; }}
QMenuBar {{ background-color: #27272a; color: #f4f4f5; border-bottom: 1px solid #3f3f46; {COMMON_FONT} }}
QMenuBar::item {{ background-color: transparent; padding: 6px 14px; margin: 0px; }}
QMenuBar::item:selected {{ background-color: #4f46e5; border-radius: 6px; }}
QMenu {{ background-color: #27272a; color: #f4f4f5; border: 1px solid #3f3f46; border-radius: 8px; padding: 4px; {COMMON_FONT} }}
QMenu::item {{ padding: 6px 24px; border-radius: 6px; }}
QMenu::item:selected {{ background-color: #4f46e5; }}
QMenu::separator {{ height: 1px; background-color: #3f3f46; margin: 6px 4px; }}
QStatusBar {{ background-color: #27272a; color: #d4d4d8; border-top: 1px solid #3f3f46; {COMMON_FONT} }}
QDialog {{ background-color: #27272a; color: #f4f4f5; {COMMON_FONT} }}
QLabel {{ color: #d4d4d8; {COMMON_FONT} }}
QGroupBox {{ color: #f4f4f5; border: 1px solid #3f3f46; border-radius: 8px; margin-top: 10px; font-weight: bold; background-color: #27272a; {COMMON_FONT} }}
QGroupBox::title {{ subcontrol-origin: margin; left: 14px; padding: 0 6px; color: #818cf8; font-weight: bold; }}
QPushButton {{ background-color: #4f46e5; color: white; border: none; border-radius: 6px; padding: 6px 14px; font-weight: 500; {COMMON_FONT} }}
QPushButton:hover {{ background-color: #6366f1; }}
QPushButton:pressed {{ background-color: #4338ca; }}
QPushButton:disabled {{ background-color: #3f3f46; color: #71717a; }}
QPushButton#danger {{ background-color: #ef4444; }}
QPushButton#danger:hover {{ background-color: #f87171; }}
QPushButton#success {{ background-color: #10b981; }}
QPushButton#success:hover {{ background-color: #34d399; }}
QComboBox {{ background-color: #3f3f46; color: #f4f4f5; border: 1px solid #52525b; border-radius: 6px; padding: 4px 8px; {COMMON_FONT} }}
QComboBox::drop-down {{ border-left: 1px solid #52525b; width: 22px; }}
QComboBox::down-arrow {{ border-left: 4px solid transparent; border-right: 4px solid transparent; border-top: 5px solid #d4d4d8; margin-right: 4px; }}
QComboBox QAbstractItemView {{ background-color: #3f3f46; color: #f4f4f5; border: 1px solid #52525b; border-radius: 6px; selection-background-color: #4f46e5; outline: none; }}
QLineEdit {{ background-color: #3f3f46; color: #f4f4f5; border: 1px solid #52525b; border-radius: 6px; padding: 6px 10px; {COMMON_FONT} }}
QLineEdit:focus {{ border: 1px solid #818cf8; }}
QSpinBox, QDoubleSpinBox {{ background-color: #3f3f46; color: #f4f4f5; border: 1px solid #52525b; border-radius: 6px; padding: 4px; {COMMON_FONT} }}
QCheckBox, QRadioButton {{ color: #d4d4d8; spacing: 6px; {COMMON_FONT} }}
QCheckBox::indicator, QRadioButton::indicator {{ width: 14px; height: 14px; border-radius: 3px; background-color: #3f3f46; border: 1px solid #52525b; }}
QCheckBox::indicator:checked, QRadioButton::indicator:checked {{ background-color: #4f46e5; border-color: #4f46e5; }}
QListWidget {{ background-color: #27272a; color: #f4f4f5; border: 1px solid #3f3f46; border-radius: 6px; padding: 4px; outline: none; {COMMON_FONT} }}
QListWidget::item {{ padding: 4px; border-radius: 4px; margin-bottom: 2px; }}
QListWidget::item:selected {{ background-color: #4f46e5; }}
QListWidget::item:hover:!selected {{ background-color: #3f3f46; }}
QProgressBar {{ border: 1px solid #3f3f46; border-radius: 6px; text-align: center; background-color: #27272a; color: #f4f4f5; font-weight: bold; {COMMON_FONT} }}
QProgressBar::chunk {{ background-color: #6366f1; border-radius: 4px; }}
QTabWidget::pane {{ border: 1px solid #3f3f46; border-radius: 8px; background-color: #27272a; }}
QTabBar::tab {{ background-color: #3f3f46; color: #d4d4d8; border: none; border-top-left-radius: 6px; border-top-right-radius: 6px; padding: 6px 14px; margin-right: 2px; font-family: 'Segoe UI', 'Inter', 'Roboto', sans-serif; }}
QTabBar::tab:selected {{ background-color: #4f46e5; color: #ffffff; }}
QTabBar::tab:hover:!selected {{ background-color: #52525b; }}
QScrollBar:vertical {{ border: none; background-color: transparent; width: 10px; margin: 0; }}
QScrollBar::handle:vertical {{ background-color: #52525b; border-radius: 5px; min-height: 24px; margin: 1px; }}
QScrollBar::handle:vertical:hover {{ background-color: #71717a; }}
QScrollBar:horizontal {{ border: none; background-color: transparent; height: 10px; margin: 0; }}
QScrollBar::handle:horizontal {{ background-color: #52525b; border-radius: 5px; min-width: 24px; margin: 1px; }}
QScrollBar::handle:horizontal:hover {{ background-color: #71717a; }}
QDialogButtonBox QPushButton {{ min-width: 90px; }}
QTreeWidget {{ background-color: #27272a; color: #f4f4f5; border: 1px solid #3f3f46; border-radius: 6px; padding: 4px; outline: none; {COMMON_FONT} }}
QTreeWidget::item {{ padding: 4px; border-radius: 4px; }}
QTreeWidget::item:selected {{ background-color: #4f46e5; }}
QTreeWidget::item:hover:!selected {{ background-color: #3f3f46; }}
QHeaderView::section {{ background-color: #18181b; color: #d4d4d8; border: none; border-bottom: 2px solid #3f3f46; padding: 6px; {COMMON_FONT} }}
QTextEdit, QPlainTextEdit {{ background-color: #3f3f46; color: #f4f4f5; border: 1px solid #52525b; border-radius: 6px; padding: 8px; selection-background-color: #4f46e5; {COMMON_FONT} }}
QTableWidget {{ background-color: #27272a; color: #f4f4f5; border: 1px solid #3f3f46; gridline-color: #3f3f46; selection-background-color: #4f46e5; border-radius: 6px; outline: none; {COMMON_FONT} }}
"""

# Светлая тема (Light Clean Crisp Mode)
LIGHT_STYLE = f"""
QMainWindow {{ background-color: #f8fafc; {COMMON_FONT} }}
QMenuBar {{ background-color: #ffffff; color: #1e293b; border-bottom: 1px solid #e2e8f0; }}
QMenuBar::item {{ background-color: transparent; padding: 6px 14px; margin: 0px; }}
QMenuBar::item:selected {{ background-color: #3b82f6; color: #ffffff; border-radius: 6px; }}
QMenu {{ background-color: #ffffff; color: #1e293b; border: 1px solid #e2e8f0; border-radius: 8px; padding: 4px; }}
QMenu::item {{ padding: 6px 24px; border-radius: 6px; }}
QMenu::item:selected {{ background-color: #3b82f6; color: #ffffff; }}
QMenu::separator {{ height: 1px; background-color: #e2e8f0; margin: 6px 4px; }}
QStatusBar {{ background-color: #ffffff; color: #475569; border-top: 1px solid #e2e8f0; }}
QDialog {{ background-color: #ffffff; color: #1e293b; }}
QLabel {{ color: #334155; }}
QGroupBox {{ color: #1e293b; border: 1px solid #cbd5e1; border-radius: 8px; margin-top: 10px; font-weight: bold; background-color: #ffffff; }}
QGroupBox::title {{ subcontrol-origin: margin; left: 14px; padding: 0 6px; color: #3b82f6; font-weight: bold; }}
QPushButton {{ background-color: #3b82f6; color: white; border: none; border-radius: 6px; padding: 6px 14px; font-weight: 500; {COMMON_FONT} }}
QPushButton:hover {{ background-color: #2563eb; }}
QPushButton:pressed {{ background-color: #1d4ed8; }}
QPushButton:disabled {{ background-color: #e2e8f0; color: #94a3b8; }}
QPushButton#danger {{ background-color: #ef4444; }}
QPushButton#success {{ background-color: #10b981; }}
QComboBox {{ background-color: #f1f5f9; color: #1e293b; border: 1px solid #cbd5e1; border-radius: 6px; padding: 4px 8px; }}
QComboBox::drop-down {{ border-left: 1px solid #cbd5e1; width: 22px; }}
QComboBox::down-arrow {{ border-left: 4px solid transparent; border-right: 4px solid transparent; border-top: 5px solid #334155; margin-right: 4px; }}
QComboBox QAbstractItemView {{ background-color: #ffffff; color: #1e293b; border: 1px solid #cbd5e1; border-radius: 6px; selection-background-color: #3b82f6; selection-color: white; outline: none; }}
QLineEdit {{ background-color: #ffffff; color: #1e293b; border: 1px solid #cbd5e1; border-radius: 6px; padding: 6px 10px; }}
QLineEdit:focus {{ border: 1px solid #3b82f6; }}
QSpinBox, QDoubleSpinBox {{ background-color: #ffffff; color: #1e293b; border: 1px solid #cbd5e1; border-radius: 6px; padding: 4px; }}
QRadioButton, QCheckBox {{ color: #334155; spacing: 6px; {COMMON_FONT} }}
QRadioButton::indicator, QCheckBox::indicator {{ width: 14px; height: 14px; border-radius: 3px; background-color: #ffffff; border: 1px solid #cbd5e1; }}
QRadioButton::indicator:checked, QCheckBox::indicator:checked {{ background-color: #3b82f6; border-color: #3b82f6; }}
QListWidget {{ background-color: #ffffff; color: #1e293b; border: 1px solid #cbd5e1; border-radius: 6px; padding: 4px; outline: none; {COMMON_FONT} }}
QListWidget::item {{ padding: 4px; border-radius: 4px; margin-bottom: 2px; }}
QListWidget::item:selected {{ background-color: #3b82f6; color: white; }}
QListWidget::item:hover:!selected {{ background-color: #f1f5f9; }}
QProgressBar {{ border: 1px solid #cbd5e1; border-radius: 6px; text-align: center; background-color: #f8fafc; color: #1e293b; font-weight: bold; {COMMON_FONT} }}
QProgressBar::chunk {{ background-color: #3b82f6; border-radius: 4px; }}
QTabWidget::pane {{ border: 1px solid #cbd5e1; border-radius: 8px; background-color: #ffffff; }}
QTabBar::tab {{ background-color: #e2e8f0; color: #475569; border: none; border-top-left-radius: 6px; border-top-right-radius: 6px; padding: 6px 14px; margin-right: 2px; font-family: 'Segoe UI', 'Inter', 'Roboto', sans-serif; }}
QTabBar::tab:selected {{ background-color: #ffffff; color: #1e293b; }}
QScrollBar:vertical {{ border: none; background-color: transparent; width: 10px; margin: 0; }}
QScrollBar::handle:vertical {{ background-color: #cbd5e1; border-radius: 5px; min-height: 24px; margin: 1px; }}
QScrollBar::handle:horizontal {{ background-color: #cbd5e1; border-radius: 5px; min-width: 24px; margin: 1px; }}
QTreeWidget {{ background-color: #ffffff; color: #1e293b; border: 1px solid #cbd5e1; border-radius: 6px; padding: 4px; outline: none; {COMMON_FONT} }}
QTreeWidget::item:selected {{ background-color: #3b82f6; color: white; }}
QHeaderView::section {{ background-color: #f8fafc; color: #475569; border: none; border-bottom: 2px solid #cbd5e1; padding: 6px; {COMMON_FONT} }}
QTextEdit, QPlainTextEdit {{ background-color: #ffffff; color: #1e293b; border: 1px solid #cbd5e1; border-radius: 6px; padding: 8px; }}
QTableWidget {{ background-color: #ffffff; color: #1e293b; border: 1px solid #cbd5e1; gridline-color: #e2e8f0; selection-background-color: #3b82f6; selection-color: white; border-radius: 6px; outline: none; {COMMON_FONT} }}
"""

# Высококонтрастная тема
HIGH_CONTRAST_STYLE = f"""
QMainWindow {{ background-color: #000000; {COMMON_FONT} }}
QMenuBar {{ background-color: #000000; color: #ffffff; border-bottom: 2px solid #ffff00; {COMMON_FONT} }}
QMenuBar::item:selected {{ background-color: #ffff00; color: #000000; }}
QMenu {{ background-color: #000000; color: #ffffff; border: 2px solid #ffffff; {COMMON_FONT} }}
QMenu::item:selected {{ background-color: #ffff00; color: #000000; }}
QStatusBar {{ background-color: #000000; color: #ffffff; border-top: 2px solid #ffff00; {COMMON_FONT} }}
QDialog {{ background-color: #000000; color: #ffffff; {COMMON_FONT} }}
QLabel {{ color: #ffffff; font-weight: bold; {COMMON_FONT} }}
QGroupBox {{ color: #ffffff; border: 2px solid #ffff00; border-radius: 6px; margin-top: 10px; font-weight: bold; background-color: #000000; {COMMON_FONT} }}
QGroupBox::title {{ left: 10px; padding: 0 4px; color: #ffff00; }}
QPushButton {{ background-color: #000000; color: #ffffff; border: 2px solid #ffffff; border-radius: 6px; padding: 6px 14px; font-weight: bold; {COMMON_FONT} }}
QPushButton:hover {{ background-color: #ffff00; color: #000000; }}
QPushButton:pressed {{ background-color: #00ff00; color: #000000; }}
QComboBox {{ background-color: #000000; color: #ffffff; border: 2px solid #ffffff; border-radius: 6px; padding: 6px 8px; {COMMON_FONT} }}
QComboBox::drop-down {{ border-left: 2px solid #ffffff; width: 22px; }}
QComboBox::down-arrow {{ border-left: 4px solid transparent; border-right: 4px solid transparent; border-top: 5px solid #ffffff; margin-right: 4px; }}
QComboBox QAbstractItemView {{ background-color: #000000; color: #ffffff; border: 2px solid #ffffff; selection-background-color: #ffff00; selection-color: #000000; }}
QLineEdit, QSpinBox, QDoubleSpinBox {{ background-color: #000000; color: #ffffff; border: 2px solid #ffffff; border-radius: 6px; padding: 6px; {COMMON_FONT} }}
QRadioButton, QCheckBox {{ color: #ffffff; {COMMON_FONT} }}
QRadioButton::indicator, QCheckBox::indicator {{ width: 14px; height: 14px; background-color: #000000; border: 2px solid #ffffff; }}
QRadioButton::indicator:checked, QCheckBox::indicator:checked {{ background-color: #ffff00; border-color: #ffff00; }}
QListWidget, QTreeWidget, QTableWidget {{ background-color: #000000; color: #ffffff; border: 2px solid #ffffff; border-radius: 6px; padding: 4px; {COMMON_FONT} }}
QListWidget::item:selected, QTreeWidget::item:selected {{ background-color: #ffff00; color: #000000; }}
QProgressBar {{ border: 2px solid #ffffff; border-radius: 6px; background-color: #000000; color: #ffffff; {COMMON_FONT} }}
QProgressBar::chunk {{ background-color: #ffff00; border-radius: 4px; }}
QTabWidget::pane {{ border: 2px solid #ffffff; border-radius: 6px; background-color: #000000; }}
QTabBar::tab {{ background-color: #000000; color: #ffffff; border: 2px solid #ffffff; padding: 6px 16px; {COMMON_FONT} }}
QTabBar::tab:selected {{ background-color: #ffff00; color: #000000; }}
QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{ background-color: #ffff00; border-radius: 4px; }}
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