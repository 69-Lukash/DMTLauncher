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

    def save_as_preset(self):
        preset_name = self.server_data.get("name", "Server Preset").strip()
        if len(preset_name) > 30:
            preset_name = preset_name[:27] + "..."
            
        mods = []
        for mod in self.server_data.get("mods", []):
            mod_id = str(mod.get("fileId", mod.get("steamWorkshopId", "")))
            if mod_id.isdigit():
                mods.append(int(mod_id))
                
        import os
        import dmtl_core
        from utils.paths import get_data_dir
        from PyQt6.QtWidgets import QMessageBox
        
        presets_dir = os.path.join(get_data_dir(), "presets")
        os.makedirs(presets_dir, exist_ok=True)
        
        final_name = preset_name
        counter = 1
        while os.path.exists(os.path.join(presets_dir, f"{final_name}.dmtlp")):
            final_name = f"{preset_name} ({counter})"
            counter += 1
            
        try:
            dmtl_core.export_preset(os.path.join(presets_dir, f"{final_name}.dmtlp"), final_name, mods)
            QMessageBox.information(self, "Success", f"Preset '{final_name}' saved!\nSwitch to the Local Game tab to see it.")
        except Exception as e:
            print(f"Error saving preset: {e}")
            QMessageBox.critical(self, "Error", f"Failed to save preset: {e}")