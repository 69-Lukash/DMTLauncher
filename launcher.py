import sys
from PyQt6.QtWidgets import QApplication
from ui.main_window import DMTLMainWindow

if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] in ("sync", "delete"):
        from core.steam_cmd import main
        main()
        sys.exit(0)

    app = QApplication(sys.argv)

    window = DMTLMainWindow()
    window.show()

    sys.exit(app.exec())