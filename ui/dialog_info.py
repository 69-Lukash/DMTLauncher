import os
from PyQt6.QtWidgets import QDialog, QApplication
from PyQt6 import uic

class ServerInfoDialog(QDialog):
    def __init__(self, server_data, ping, parent=None):
        super().__init__(parent)
        
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        ui_path = os.path.join(BASE_DIR, 'assets', 'dialog_info.ui')
        uic.loadUi(ui_path, self)
        
        self.server_data = server_data
        self.ping = ping
        self.address = ""
        
        self.populate_data()
        
        self.btn_copy_ip.clicked.connect(self.copy_ip)

    def populate_data(self):
        name = str(self.server_data.get("name", "Unknown Server"))
        ip = str(self.server_data.get("ip", self.server_data.get("endpoint", {}).get("ip", "")))
        port = str(self.server_data.get("gamePort", self.server_data.get("port", self.server_data.get("endpoint", {}).get("port", ""))))
        self.address = f"{ip}:{port}"
        
        players = f"{self.server_data.get('players', 0)}/{self.server_data.get('maxplayers', self.server_data.get('maxPlayers', 0))}"
        is_password = self.server_data.get("password", False)
        time = str(self.server_data.get("dayTime", self.server_data.get("time", "Unknown")))
        location = str(self.server_data.get("country", "Unknown"))
        mods = self.server_data.get("mods", [])

        self.lbl_name.setText(name)
        self.lbl_ip.setText(self.address)
        self.lbl_ping.setText(str(self.ping))
        self.lbl_players.setText(players)
        self.lbl_password.setText("Yes 🔒" if is_password else "No 🔓")
        self.lbl_time.setText(time)
        self.lbl_location.setText(location)
        self.lbl_mods_count.setText(str(len(mods)))

        self.list_mods.clear()
        for mod in mods:
            mod_name = mod.get("name", mod.get("title", str(mod)))
            self.list_mods.addItem(mod_name)

    def copy_ip(self):
        QApplication.clipboard().setText(self.address)