from steam.manager import SteamManager

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

    def set_mods_data(self, data):
        self.mods_data = data
        self.render_mods()

    def filter_mods(self, text):
        self.render_mods(text.strip().lower())

    def render_mods(self, search_query=""):
        self.table_mods.setRowCount(0)
        
        for mod_id, d_mod in self.downloading_mods.items():
            if search_query and search_query not in d_mod["name"].lower():
                continue
                
            self.table_builder.insert_mod_row(
                f"⬇️ {d_mod['name']} [Downloading...]", 
                "Steam",
                d_mod["size"], 
                lambda r, c: None
            )

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
            
        if col == 3:
            self.sync_mod(mod_id)
        elif col == 4:
            self.delete_mod(mod_id, mod, row)
            

    def sync_mod(self, mod_id: int):
        self.steam_mgr.sync_mod(mod_id)
        print(f"[ModController] Sync command for {mod_id} sent to Steamworks.")

    def sync_all_mods(self):
        mod_ids = []
        for mod in self.mods_data:
            pub_id = mod.get("published_id")
            if pub_id and str(pub_id).isdigit():
                mod_ids.append(int(pub_id))
        
        if mod_ids:
            print(f"[ModController] Batch syncing {len(mod_ids)} mods...")
            self.steam_mgr.sync_mods_batch(mod_ids)
            
    def delete_mod(self, mod_id: int, mod: dict, row: int):
        self.steam_mgr.unsubscribe_mod(mod_id)
        self.table_mods.removeRow(row)
        if mod in self.mods_data:
            self.mods_data.remove(mod) 
        print(f"[ModController] Mod {mod_id} deleted via Steamworks.")