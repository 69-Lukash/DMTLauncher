from core.steam_manager import SteamManager

class ModController:
    def __init__(self, table_mods):
        self.table_mods = table_mods
        self.mods_data = [] 
        self.steam_mgr = SteamManager()

    def set_mods_data(self, data):
        self.mods_data = data

    def handle_mod_action(self, row, col):
        mod_name_item = self.table_mods.item(row, 0)
        if not mod_name_item:
            return
            
        display_name = mod_name_item.text()
        
        mod = next((m for m in self.mods_data if m["display_name"] == display_name), None)
        if not mod or not mod.get("published_id"):
            print(f"[ModController] Error: Valid Steam ID not found for {display_name}.")
            return
            
        try:
            mod_id = int(mod["published_id"])
        except ValueError:
            print("[ModController] Error: Invalid Steam ID format.")
            return
            
        if col == 3: # Sync
            self.sync_mod(mod_id)
        elif col == 4: # Delete
            self.delete_mod(mod_id, mod, row)

    def sync_mod(self, mod_id: int):
        self.steam_mgr.sync_mod(mod_id)
        print(f"[ModController] Sync command for {mod_id} sent to Steamworks.")
            
    def delete_mod(self, mod_id: int, mod: dict, row: int):
        self.steam_mgr.unsubscribe_mod(mod_id)
        self.table_mods.removeRow(row)
        if mod in self.mods_data:
            self.mods_data.remove(mod) 
        print(f"[ModController] Mod {mod_id} deleted via Steamworks.")