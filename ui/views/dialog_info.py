import os
import sys
from PyQt6.QtWidgets import QDialog, QApplication
from PyQt6.QtCore import Qt
from PyQt6 import uic

class ServerInfoDialog(QDialog):
    def __init__(self, server_data, ping, parent=None):
        super().__init__(parent)
        
        if getattr(sys, 'frozen', False):
            BASE_DIR = sys._MEIPASS if hasattr(sys, '_MEIPASS') else os.path.dirname(sys.executable)
        else:
            BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
        ui_path = os.path.join(BASE_DIR, 'assets', 'dialog_info.ui')
        uic.loadUi(ui_path, self)
        
        self.server_data = server_data
        self.ping = ping
        self.address = ""
        
        self.populate_data()
        
        self.btn_copy_ip.clicked.connect(self.copy_modlist)

    def populate_data(self):
        name = str(self.server_data.get("name", "Unknown Server"))
        ip = str(self.server_data.get("ip", ""))
        port = str(self.server_data.get("gamePort", ""))
        self.address = f"{ip}:{port}"
        
        players = f"{self.server_data.get('players', 0)}/{self.server_data.get('maxplayers', 0)}"
        is_password = self.server_data.get("password", False)
        
        time = str(self.server_data.get("dayTime", "Unknown"))
        country = str(self.server_data.get("country", "Unknown"))
        mods = self.server_data.get("mods", [])

        html_content = f"""
        <div style="font-family: 'Segoe UI', Arial, sans-serif; font-size: 14px; line-height: 1.4; color: #d4c8e3;">
            <p style="font-size: 16px; margin-bottom: 8px;"><b>Name:</b> {name}</p>
            <p style="margin: 4px 0;"><b>IP:Port:</b> {self.address}</p>
            <p style="margin: 4px 0;"><b>Ping:</b> {self.ping}</p>
            <p style="margin: 4px 0;"><b>Players:</b> {players}</p>
            <p style="margin: 4px 0;"><b>Password:</b> {"Yes 🔒" if is_password else "No 🔓"}</p>
            <p style="margin: 4px 0;"><b>In-Game Time:</b> {time}</p>
            <p style="margin: 4px 0;"><b>Country:</b> {country}</p>
            <p style="margin: 4px 0;"><b>Mods Count:</b> {len(mods)}</p>
        </div>
        """
        self.info_browser.setHtml(html_content)

        self.list_mods.clear()
        for mod in mods:
            mod_name = mod.get("name", mod.get("title", str(mod)))
            self.list_mods.addItem(mod_name)

    def copy_modlist(self):
        mods = []
        for i in range(self.list_mods.count()):
            mods.append(self.list_mods.item(i).text())
        
        if mods:
            QApplication.clipboard().setText("\n".join(mods))
        else:
            QApplication.clipboard().setText("No mods")