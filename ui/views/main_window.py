import sys
import os
from PyQt6 import uic
from PyQt6.QtWidgets import QMainWindow, QPushButton, QWidget, QHBoxLayout 
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QIcon

from ui.components.icon_factory import create_gear_icon
from ui.components.table_builder import TableBuilder
from utils.logger import logger

class DMTLMainWindow(QMainWindow):
    def __init__(self, *args, **kwargs):
        super(DMTLMainWindow, self).__init__(*args, **kwargs)

        if getattr(sys, 'frozen', False):
            BASE_DIR = sys._MEIPASS if hasattr(sys, '_MEIPASS') else os.path.dirname(sys.executable)
        else:
            BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            
        assets_dir = os.path.join(BASE_DIR, "assets")
        self.setWindowIcon(QIcon(os.path.join(assets_dir, "icon.png")))

        uic.loadUi(os.path.join(assets_dir, "main.ui"), self)
        self.tab_servers = uic.loadUi(os.path.join(assets_dir, "tab_servers.ui"))
        self.tab_mods = uic.loadUi(os.path.join(assets_dir, "tab_mods.ui"))
        self.settings_panel = uic.loadUi(os.path.join(assets_dir, "panel_settings.ui"))

        self.tabs.addTab(self.tab_servers, self.tr("Servers"))
        self.tabs.addTab(self.tab_mods, self.tr("Mods"))
        
        self.corner_container = QWidget()
        self.corner_layout = QHBoxLayout(self.corner_container)
        self.corner_layout.setContentsMargins(0, 0, 0, 0)
        self.corner_layout.setSpacing(10)

        self.btn_direct_connect = QPushButton(self.tr("🔌 Direct Connect"))
        self.btn_direct_connect.setObjectName("btn_direct_connect")
        self.btn_direct_connect.setCursor(Qt.CursorShape.PointingHandCursor)

        self.btn_settings = QPushButton()
        self.btn_settings.setObjectName("btn_settings")
        self.btn_settings.setIcon(create_gear_icon())
        self.btn_settings.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_settings.clicked.connect(self.toggle_settings)

        self.corner_layout.addWidget(self.btn_direct_connect)
        self.corner_layout.addWidget(self.btn_settings)
        self.tabs.setCornerWidget(self.corner_container, Qt.Corner.TopRightCorner)

        self.main_layout.addWidget(self.settings_panel)
        self.settings_panel.setMaximumWidth(0)

        if not sys.platform.startswith("linux") and hasattr(self.settings_panel, 'linux_warning'):
            self.settings_panel.linux_warning.hide()

        self.table_builder = TableBuilder(self.tab_servers.table_servers, self.tab_mods.table_mods)
        
        self.apply_stylesheet()
        self.table_builder.setup_table_columns(self.sort_servers_table)

    def toggle_settings(self):
        width = self.settings_panel.width()
        target_width = 300 if width == 0 else 0
        self.animation = QPropertyAnimation(self.settings_panel, b"maximumWidth")
        self.animation.setDuration(300)
        self.animation.setStartValue(width)
        self.animation.setEndValue(target_width)
        self.animation.setEasingCurve(QEasingCurve.Type.InOutQuart)
        self.animation.start()

    def sort_servers_table(self, col):
        self.table_builder.sort_servers_table(col)

    def apply_stylesheet(self):
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        stylesheet_path = os.path.join(BASE_DIR, "assets", "style.qss")
        try:
            with open(stylesheet_path, "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())
        except IOError as e:
            logger.error(f"Failed to load QSS stylesheet: {e}", exc_info=True)