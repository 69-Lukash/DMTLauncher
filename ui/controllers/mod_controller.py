import copy
import sys
import os
import subprocess

from steam.manager import SteamManager
from PyQt6.QtCore import Qt, QCoreApplication
from utils.logger import logger

class ModController:
    def __init__(self, view):
        self.view = view
        self.tab_mods = view.tab_mods
        self.table_mods = view.tab_mods.table_mods
        self.table_builder = view.table_builder
        
        self.mods_data = [] 
        self.downloading_mods = {}
        self.steam_mgr = SteamManager()
        
        self._setup_connections()

    def _setup_connections(self):
            self.tab_mods.search_mod.textChanged.connect(self.filter_mods)
            self.tab_mods.btn_sync_all.clicked.connect(self.sync_all_mods)
            self.table_mods.cellDoubleClicked.connect(self.open_mod_folder)

    def set_mods_data(self, data):
        self.mods_data = data
        self.render_mods()

    def filter_mods(self, text):
        self.render_mods(text.strip().lower())

    def render_mods(self, search_query=""):
        
        self.table_mods.setRowCount(0)
        
        downloading_text = QCoreApplication.translate("ModController", "[Downloading...]")
        
        for mod_id, d_mod in self.downloading_mods.items():
            if search_query and search_query not in d_mod["name"].lower():
                continue
                
            self.table_builder.insert_mod_row(
                f"⬇️ {d_mod['name']} {downloading_text}", 
                "Steam",
                d_mod["size"], 
                lambda r, c: None
            )
            row = self.table_mods.rowCount() - 1
            self.table_mods.item(row, 0).setData(Qt.ItemDataRole.UserRole, mod_id)

        for mod in self.mods_data:
            display_name = mod.get("display_name", "")
            
            if search_query and search_query not in display_name.lower():
                continue
                
            self.table_builder.insert_mod_row(
                display_name, 
                mod.get("author", "Unknown"), 
                mod.get("size", "0 B"), 
                self.handle_mod_action 
            )
            row = self.table_mods.rowCount() - 1
            mod_id = mod.get("published_id")
            if mod_id:
                self.table_mods.item(row, 0).setData(Qt.ItemDataRole.UserRole, str(mod_id))

    def update_download_progress(self):
        for row in range(self.table_mods.rowCount()):
            name_item = self.table_mods.item(row, 0)
            if not name_item: 
                continue
            
            mod_id = name_item.data(Qt.ItemDataRole.UserRole)
            
            if mod_id and mod_id in self.downloading_mods:
                size_item = self.table_mods.item(row, 2)
                if size_item:
                    size_item.setText(self.downloading_mods[mod_id]["size"])

    def handle_mod_action(self, row, col):
        mod_name_item = self.table_mods.item(row, 0)
        if not mod_name_item:
            return
            
        display_name = mod_name_item.text()
        target_id = mod_name_item.data(Qt.ItemDataRole.UserRole)
        
        mod = next((m for m in self.mods_data if str(m.get("published_id")) == str(target_id)), None)
        
        if not mod or not mod.get("published_id"):
            logger.warning(f"Valid Steam ID not found for {display_name}.")
            return
            
        try:
            mod_id = int(mod["published_id"])
        except ValueError:
            logger.error("Invalid Steam ID format.")
            return
            
        if col == 3:
            self.sync_mod(mod_id)
        elif col == 4:
            self.delete_mod(mod_id, mod, row)
            

    def sync_mod(self, mod_id: int):
        self.steam_mgr.sync_mod(mod_id)
        logger.info(f"Sync command for {mod_id} sent to Steamworks.")

    def sync_all_mods(self):
        mod_ids = []
        for mod in self.mods_data:
            pub_id = mod.get("published_id")
            if pub_id and str(pub_id).isdigit():
                mod_ids.append(int(pub_id))
        
        if mod_ids:
            logger.info(f"Batch syncing {len(mod_ids)} mods...")
            self.steam_mgr.sync_mods_batch(mod_ids)
            
    def delete_mod(self, mod_id: int, mod: dict, row: int):
        self.steam_mgr.unsubscribe_mod(mod_id)
        self.table_mods.removeRow(row)
        if mod in self.mods_data:
            self.mods_data.remove(mod) 
        logger.info(f"Mod {mod_id} deleted via Steamworks.")

    def open_mod_folder(self, row, col):
        mod_name_item = self.table_mods.item(row, 0)
        if not mod_name_item:
            return
            
        target_id = mod_name_item.data(Qt.ItemDataRole.UserRole)
        mod = next((m for m in self.mods_data if str(m.get("published_id")) == str(target_id)), None)
        
        if mod and "path" in mod:
            folder_path = os.path.normpath(mod["path"])
            

            clean_env = copy.deepcopy(os.environ)
            
            if sys.platform != "win32":
                if "LD_LIBRARY_PATH_ORIG" in clean_env:
                    clean_env["LD_LIBRARY_PATH"] = clean_env["LD_LIBRARY_PATH_ORIG"]
                else:
                    clean_env.pop("LD_LIBRARY_PATH", None)
                    
            try:
                if sys.platform == "win32":
                    subprocess.Popen(
                        ["explorer", folder_path], 
                        env=clean_env, 
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
                else:
                    subprocess.Popen(["xdg-open", folder_path], env=clean_env)
            except Exception as e:
                logger.error(f"Error opening folder: {e}", exc_info=True)