import os
import sys
import dmtl_core

from PyQt6.QtWidgets import QDialog, QApplication, QMessageBox
from PyQt6.QtCore import QCoreApplication, Qt
from PyQt6 import uic
        
from utils.paths import get_data_dir

class ServerInfoDialog(QDialog):
    def __init__(self, server_data, ping, parent=None):
        super().__init__(parent)
        
        if getattr(sys, 'frozen', False):
            BASE_DIR = sys._MEIPASS if hasattr(sys, '_MEIPASS') else os.path.dirname(sys.executable)
        else:
            BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
        ui_path = os.path.join(BASE_DIR, 'assets', 'dialog_info.ui')
        uic.loadUi(ui_path, self)

        self.setSizeGripEnabled(True)
        self.setMinimumSize(400, 500)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowMaximizeButtonHint)
        
        self.server_data = server_data
        self.ping = ping
        self.address = ""
        
        self.populate_data()
        
        self.btn_copy_ip.clicked.connect(self.copy_modlist)
        self.btn_save_preset.clicked.connect(self.save_as_preset)

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

        t_name = QCoreApplication.translate("ServerInfoDialog", "Name:")
        t_ip = QCoreApplication.translate("ServerInfoDialog", "IP:Port:")
        t_ping = QCoreApplication.translate("ServerInfoDialog", "Ping:")
        t_players = QCoreApplication.translate("ServerInfoDialog", "Players:")
        t_password = QCoreApplication.translate("ServerInfoDialog", "Password:")
        t_time = QCoreApplication.translate("ServerInfoDialog", "In-Game Time:")
        t_country = QCoreApplication.translate("ServerInfoDialog", "Country:")
        t_mods_count = QCoreApplication.translate("ServerInfoDialog", "Mods Count:")
        
        val_yes = QCoreApplication.translate("ServerInfoDialog", "Yes 🔒")
        val_no = QCoreApplication.translate("ServerInfoDialog", "No 🔓")

        html_content = f"""
        <div class="server-info-container">
            <p class="server-name"><b>{t_name}</b> {name}</p>
            <p><b>{t_ip}</b> {self.address}</p>
            <p><b>{t_ping}</b> {self.ping}</p>
            <p><b>{t_players}</b> {players}</p>
            <p><b>{t_password}</b> {val_yes if is_password else val_no}</p>
            <p><b>{t_time}</b> {time}</p>
            <p><b>{t_country}</b> {country}</p>
            <p><b>{t_mods_count}</b> {len(mods)}</p>
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

    def save_as_preset(self):
        preset_name = self.server_data.get("name", "Server Preset").strip()
        if len(preset_name) > 30:
            preset_name = preset_name[:27] + "..."
            
        mods = []
        for mod in self.server_data.get("mods", []):
            mod_id = str(mod.get("fileId", mod.get("steamWorkshopId", "")))
            if mod_id.isdigit():
                mods.append(int(mod_id))
                
        
        presets_dir = os.path.join(get_data_dir(), "presets")
        os.makedirs(presets_dir, exist_ok=True)
        
        final_name = preset_name
        counter = 1
        while os.path.exists(os.path.join(presets_dir, f"{final_name}.dmtlp")):
            final_name = f"{preset_name} ({counter})"
            counter += 1
            
        try:
            dmtl_core.export_preset(os.path.join(presets_dir, f"{final_name}.dmtlp"), final_name, mods)
            title = QCoreApplication.translate("ServerInfoDialog", "Success")
            msg = QCoreApplication.translate("ServerInfoDialog", "Preset '{0}' saved!\nSwitch to the Local Game tab to see it.").format(final_name)
            QMessageBox.information(self, title, msg)
        except Exception as e:
            print(f"Error saving preset: {e}")
            err_title = QCoreApplication.translate("ServerInfoDialog", "Error")
            err_msg = QCoreApplication.translate("ServerInfoDialog", "Failed to save preset: {0}").format(str(e))
            QMessageBox.critical(self, err_title, err_msg)