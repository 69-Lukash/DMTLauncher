import sys
import os

if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS if hasattr(sys, '_MEIPASS') else os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

if sys.platform == "win32":
    if hasattr(os, "add_dll_directory"):
        os.add_dll_directory(BASE_DIR)
    os.environ["PATH"] = BASE_DIR + os.pathsep + os.environ.get("PATH", "")
else:
    current_ld = os.environ.get("LD_LIBRARY_PATH", "")
    if BASE_DIR not in current_ld:
        os.environ["LD_LIBRARY_PATH"] = BASE_DIR + (os.pathsep + current_ld if current_ld else "")
from PyQt6.QtWidgets import QApplication
from ui.controllers.main_controller import MainController

if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] in ("sync", "delete"):
        from steam.cmd_worker import main
        main()
        sys.exit(0)

    app = QApplication(sys.argv)
    
    controller = MainController()
    controller.show()

    sys.exit(app.exec())