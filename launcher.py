import signal
import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTranslator
from pathlib import Path

from ui.controllers.main_controller import MainController
from config.manager import ConfigManager

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


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] in ("sync", "delete"):
        from steam.cmd_worker import main
        main()
        sys.exit(0)

    app = QApplication(sys.argv)

    signal.signal(signal.SIGINT, signal.SIG_DFL)
    
    if sys.platform == "win32":
        app_data = os.getenv('LOCALAPPDATA') or os.getenv('APPDATA') or os.path.expanduser('~')
        cfg_path = os.path.join(app_data, "DMTL", "config.json")
    else:
        cfg_path = os.path.join(str(Path.home()), ".config", "DMTL", "config.json")
        
    config = ConfigManager(cfg_path)
    
    translator = QTranslator()
    locale_path = os.path.join(BASE_DIR, "locales", f"{config.language}.qm")
    if os.path.exists(locale_path):
        translator.load(locale_path)
        app.installTranslator(translator)
    
    controller = MainController()
    controller.show()

    sys.exit(app.exec())