# ui/launcher.py (упрощённый)
import sys
import os
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QSurfaceFormat


project_root = os.path.dirname(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from ui.main_window import MainWindow

def main():
    fmt = QSurfaceFormat()
    fmt.setAlphaBufferSize(8)
    fmt.setRenderableType(QSurfaceFormat.OpenGL)
    QSurfaceFormat.setDefaultFormat(fmt)

    app = QApplication(sys.argv)
    window = MainWindow(    )
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()