import sys
from PyQt6.QtWidgets import QApplication
from ui.main_window import DMTLMainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    window = DMTLMainWindow()
    window.show()
    
    sys.exit(app.exec())
