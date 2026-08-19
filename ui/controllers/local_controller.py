import os
import shutil
import dmtl_core
from PyQt6.QtWidgets import QInputDialog, QMessageBox, QFileDialog, QTableWidgetItem
from PyQt6.QtCore import Qt, QThreadPool
from utils.logger import logger
from utils.paths import get_data_dir
from network.api import DependencyWorker

class CheckableModItem(QTableWidgetItem):
    def __lt__(self, other):
        if self.checkState() != other.checkState():
            return self.checkState() == Qt.CheckState.Checked
        return self.text().lower() < other.text().lower()

class LocalController:
    def __init__(self, view, config_manager, mod_controller, launch_callback):
        self.view = view
        self.tab_local = view.tab_local
        self.table_local = view.tab_local.table_local
        self.config_manager = config_manager
        self.mod_controller = mod_controller
        self.launch_callback = launch_callback
        
        # Setup presets directory
        self.presets_dir = os.path.join(get_data_dir(), "presets")
        os.makedirs(self.presets_dir, exist_ok=True)
        
        self.current_preset = None
        self.current_preset_mods = []
        self._list_loaded = False
        self._updating_ui = False
        
        self._setup_ui()
        self._setup_connections()
        self._refresh_preset_combo()

    def _setup_ui(self):
        self.table_local.horizontalHeader().setStretchLastSection(False)
        self.table_local.horizontalHeader().setSectionResizeMode(0, self.table_local.horizontalHeader().ResizeMode.Stretch)
        self.table_local.setColumnWidth(1, 100)
        self.table_local.setColumnWidth(2, 80)
        self.table_local.verticalHeader().setVisible(False)

    def _setup_connections(self):
        self.view.tabs.currentChanged.connect(self.on_tab_changed)
        self.tab_local.combo_presets.currentIndexChanged.connect(self.on_preset_selected)
        self.tab_local.btn_delete.clicked.connect(self.delete_preset)
        self.tab_local.btn_export.clicked.connect(self.export_preset)
        self.tab_local.btn_import.clicked.connect(self.import_preset)
        self.tab_local.btn_play.clicked.connect(self.launch_local)
        self.tab_local.search_local_mod.textChanged.connect(self.filter_mods)
        self.table_local.itemChanged.connect(self.on_item_checked)

    def on_tab_changed(self, index):
        if self.view.tabs.widget(index) == self.tab_local:
            if not self._list_loaded:
                self.load_mods_into_table()
                self._list_loaded = True
            
            if self.current_preset:
                self.sort_table()

    def _get_preset_path(self, name):
        return os.path.join(self.presets_dir, f"{name}.dmtlp")

    def _refresh_preset_combo(self):
        self._updating_ui = True
        self.tab_local.combo_presets.clear()
        
        self.tab_local.combo_presets.addItem("📁 Select Preset...")
        self.tab_local.combo_presets.addItem("➕ Create New Preset...")
        
        preset_files = [f for f in os.listdir(self.presets_dir) if f.endswith(".dmtlp")]
        preset_names = sorted([os.path.splitext(f)[0] for f in preset_files])
        
        for p_name in preset_names:
            self.tab_local.combo_presets.addItem(p_name)
            
        last_preset = self.config_manager.last_local_preset
        if last_preset and last_preset in preset_names:
            self.tab_local.combo_presets.setCurrentText(last_preset)
            self.current_preset = last_preset
        elif preset_names:
            first_preset = preset_names[0]
            self.tab_local.combo_presets.setCurrentText(first_preset)
            self.current_preset = first_preset
        else:
            self.tab_local.combo_presets.setCurrentIndex(0)
            self.current_preset = None
            
        self._updating_ui = False

    def _save_current_preset(self):
        if not self.current_preset: return
        path = self._get_preset_path(self.current_preset)
        try:
            dmtl_core.export_preset(path, self.current_preset, self.current_preset_mods)
        except Exception as e:
            logger.error(f"Failed to save preset {self.current_preset}: {e}")

    def on_preset_selected(self, index):
        if self._updating_ui or index == -1 or index == 0: return
        
        if index == 1:
            text, ok = QInputDialog.getText(self.view, "New Preset", "Preset Name:")
            if ok and text.strip():
                name = text.strip()
                self.current_preset = name
                self.current_preset_mods = []
                self._save_current_preset()
                self.config_manager.last_local_preset = name
                self.config_manager.save()
                self._refresh_preset_combo()
                self.tab_local.combo_presets.setCurrentText(name)
            else:
                fallback_text = self.current_preset if self.current_preset else "📁 Select Preset..."
                self.tab_local.combo_presets.setCurrentText(fallback_text)
            return

        self.current_preset = self.tab_local.combo_presets.currentText()
        self.config_manager.last_local_preset = self.current_preset
        self.config_manager.save()
        
        if self._list_loaded:
            self.apply_preset_to_table()

    def filter_mods(self, text):
        query = text.strip().lower()
        for row in range(self.table_local.rowCount()):
            item = self.table_local.item(row, 0)
            if not item: continue
            
            mod_name = item.text().lower()
            if query in mod_name:
                self.table_local.setRowHidden(row, False)
            else:
                self.table_local.setRowHidden(row, True)

    def load_mods_into_table(self):
        self._updating_ui = True
        self.table_local.setRowCount(0)
        
        for mod in self.mod_controller.mods_data:
            row = self.table_local.rowCount()
            self.table_local.insertRow(row)
            
            name_item = CheckableModItem(mod.get("display_name", "Unknown"))
            name_item.setFlags(name_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            name_item.setCheckState(Qt.CheckState.Unchecked)
            name_item.setData(Qt.ItemDataRole.UserRole, str(mod.get("published_id")))
            
            size_item = QTableWidgetItem(mod.get("size", "0 B"))
            size_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            
            sync_item = QTableWidgetItem("🔄 Sync")
            sync_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            
            self.table_local.setItem(row, 0, name_item)
            self.table_local.setItem(row, 1, size_item)
            self.table_local.setItem(row, 2, sync_item)
            
        self._updating_ui = False
        self.apply_preset_to_table()

    def apply_preset_to_table(self):
        if not self.current_preset: return
        self._updating_ui = True
        
        path = self._get_preset_path(self.current_preset)
        self.current_preset_mods = []
        
        if os.path.exists(path):
            try:
                _, mods = dmtl_core.import_preset(path)
                self.current_preset_mods = [int(m) for m in mods]
            except Exception as e:
                logger.error(f"Failed to read preset {path}: {e}")
        
        for r in range(self.table_local.rowCount()):
            item = self.table_local.item(r, 0)
            mod_id = item.data(Qt.ItemDataRole.UserRole)
            if int(mod_id) in self.current_preset_mods:
                item.setCheckState(Qt.CheckState.Checked)
            else:
                item.setCheckState(Qt.CheckState.Unchecked)
                
        self.sort_table()
        self._updating_ui = False

    def sort_table(self):
        self.table_local.sortItems(0, Qt.SortOrder.AscendingOrder)

    def on_item_checked(self, item):
        if self._updating_ui or not self.current_preset or item.column() != 0: return
        
        mod_id = int(item.data(Qt.ItemDataRole.UserRole))
        
        if item.checkState() == Qt.CheckState.Checked:
            if mod_id not in self.current_preset_mods:
                self.current_preset_mods.append(mod_id)
                self.check_dependencies(mod_id)
        else:
            if mod_id in self.current_preset_mods:
                self.current_preset_mods.remove(mod_id)
                
        self._save_current_preset()

    def check_dependencies(self, mod_id):
        worker = DependencyWorker(mod_id)
        worker.signals.finished.connect(self.on_dependencies_fetched)
        QThreadPool.globalInstance().start(worker)

    def on_dependencies_fetched(self, base_mod_id, dep_names, dep_ids):
        if not dep_ids or not self.current_preset: return
        
        missing_ids = []
        missing_names = []
        
        for i, d_id in enumerate(dep_ids):
            if d_id not in self.current_preset_mods:
                missing_ids.append(d_id)
                missing_names.append(dep_names[i])
                
        if not missing_ids: return
        
        mods_list_str = "\n".join(f"• {name}" for name in missing_names)
        
        reply = QMessageBox.question(
            self.view, 
            "Missing Dependencies", 
            f"This mod requires {len(missing_ids)} additional mod(s):\n\n{mods_list_str}\n\nEnable them automatically?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self._updating_ui = True
            
            for d_id in missing_ids:
                if d_id not in self.current_preset_mods:
                    self.current_preset_mods.append(d_id)
            self._save_current_preset()
            
            local_ids = [int(m.get("published_id")) for m in self.mod_controller.mods_data if m.get("published_id")]
            to_download = [d for d in missing_ids if d not in local_ids]
            
            if to_download:
                dl_reply = QMessageBox.question(
                    self.view,
                    "Download Required",
                    f"You are missing {len(to_download)} mod(s) from this list locally.\nStart download via Steam?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if dl_reply == QMessageBox.StandardButton.Yes:
                    self.mod_controller.steam_mgr.sync_mods_batch(to_download)
            
            self._updating_ui = False
            self.apply_preset_to_table()

    def delete_preset(self):
        if not self.current_preset: return
        
        reply = QMessageBox.question(self.view, 'Delete Preset', f"Delete preset '{self.current_preset}'?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            path = self._get_preset_path(self.current_preset)
            if os.path.exists(path):
                os.remove(path)
            self.current_preset = None
            self._refresh_preset_combo()

    def export_preset(self):
        if not self.current_preset: return
        dest_path, _ = QFileDialog.getSaveFileName(self.view, "Export Preset", f"{self.current_preset}.dmtlp", "DMTL Preset (*.dmtlp)")
        
        if dest_path:
            src_path = self._get_preset_path(self.current_preset)
            if os.path.exists(src_path):
                try:
                    shutil.copy2(src_path, dest_path)
                    QMessageBox.information(self.view, "Success", "Preset exported successfully.")
                except Exception as e:
                    logger.error(f"Export failed: {e}")
                    QMessageBox.critical(self.view, "Error", f"Failed to export: {e}")

    def import_preset(self):
        path, _ = QFileDialog.getOpenFileName(self.view, "Import Preset", "", "DMTL Preset (*.dmtlp)")
        if path:
            try:
                name, mod_ids = dmtl_core.import_preset(path)
                
                final_name = name
                counter = 1
                while os.path.exists(self._get_preset_path(final_name)):
                    final_name = f"{name} ({counter})"
                    counter += 1
                    
                dmtl_core.export_preset(self._get_preset_path(final_name), final_name, mod_ids)
                
                self.current_preset = final_name
                self.config_manager.last_local_preset = final_name
                self.config_manager.save()
                
                self._refresh_preset_combo()
                
                if self._list_loaded:
                    self.apply_preset_to_table()
                
                local_ids = [int(m.get("published_id")) for m in self.mod_controller.mods_data if m.get("published_id")]
                missing = [m for m in mod_ids if m not in local_ids]
                
                if missing:
                    reply = QMessageBox.question(
                        self.view, 
                        "Missing Mods", 
                        f"Missing {len(missing)} mods from this preset. Download them?", 
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                    )
                    if reply == QMessageBox.StandardButton.Yes:
                        self.mod_controller.steam_mgr.sync_mods_batch(missing)
                        
            except Exception as e:
                logger.error(f"Import failed: {e}")
                QMessageBox.critical(self.view, "Error", f"Failed to import: {e}")
                
    def launch_local(self):
        if not self.current_preset: return
        
        mock_server_data = {
            "name": self.current_preset,
            "ip": "",
            "gamePort": 0,
            "mods": [{"steamWorkshopId": str(m)} for m in self.current_preset_mods]
        }
        
        self.launch_callback(mock_server_data, "play")