
import sys
import traceback

def global_excepthook(exc_type, exc_value, exc_traceback):
    with open("crash.log", "w", encoding="utf-8") as f:
        traceback.print_exception(exc_type, exc_value, exc_traceback, file=f)
    traceback.print_exception(exc_type, exc_value, exc_traceback)
    sys.__excepthook__(exc_type, exc_value, exc_traceback)

sys.excepthook = global_excepthook

from ui.launcher import main

if __name__ == "__main__":
    main()