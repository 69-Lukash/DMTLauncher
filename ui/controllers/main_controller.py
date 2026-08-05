import os
import sys
from pathlib import Path
from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtCore import QThreadPool, QFileSystemWatcher, QTimer

from ui.views.main_window import DMTLMainWindow
from config.manager import ConfigManager
from ui.controllers.mod_controller import ModController
from ui.controllers.server_controller import ServerController
from steam.parser import ModParserWorker
from game.runner import GameRunner
from utils.logger import logger

class MainController:
    def __init__(self):
        self.view = DMTLMainWindow()
        
        self.config_path = self._get_config_path()
        self.config_manager = ConfigManager(self.config_path)
        
        self.mod_controller = ModController(self.view)
        self.server_controller = ServerController(self.view, self.config_manager, self.queue_launch)
        
        self.thread_pool = QThreadPool.globalInstance()
        self.active_workers = []
        self.pending_launch = None
        
        self.mod_watcher = QFileSystemWatcher()
        self.mod_watcher.directoryChanged.connect(self.on_workshop_changed)
        self.download_timer = QTimer()
        self.download_timer.timeout.connect(self.check_downloads)
        self.mod_update_timer = QTimer()
        self.mod_update_timer.setSingleShot(True)
        self.mod_update_timer.timeout.connect(self.fetch_local_mods)
        self.check_existing_downloads()

        self._setup_connections()
        
        self.server_controller.fetch_global_database()
        self.fetch_local_mods()

        self.view.settings_panel.combo_sort.setCurrentIndex(self.config_manager.default_sort)
        self.view.settings_panel.combo_sort.currentIndexChanged.connect(self.save_config)
        
        lang_index = 1 if self.config_manager.language == "uk_UA" else 0
        self.view.settings_panel.combo_lang.setCurrentIndex(lang_index)
        self.view.settings_panel.combo_lang.currentIndexChanged.connect(self.save_config)

    def _get_config_path(self):
        if sys.platform == "win32":
            app_data = os.getenv('LOCALAPPDATA') or os.getenv('APPDATA')
            data_dir = os.path.join(app_data, "DMTL")
        else:
            data_dir = os.path.join(str(Path.home()), ".config", "DMTL")
        os.makedirs(data_dir, exist_ok=True)
        return os.path.join(data_dir, "config.json")

    def _setup_connections(self):
        self.view.settings_panel.input_nick.setText(self.config_manager.nickname)
        self.view.settings_panel.input_path.setText(self.config_manager.game_path)
        self.view.settings_panel.input_nick.editingFinished.connect(self.save_config)
        self.view.settings_panel.input_path.editingFinished.connect(self.save_config)
        self.view.settings_panel.btn_browse.clicked.connect(self.browse_path)
        if hasattr(self.view.settings_panel, 'input_params'):
            self.view.settings_panel.input_params.setText(self.config_manager.launch_params)
            self.view.settings_panel.input_params.editingFinished.connect(self.save_config)
            
        if hasattr(self.view.settings_panel, 'btn_about'):
            self.view.settings_panel.btn_about.clicked.connect(self.show_about_dialog)

        if hasattr(self.view.settings_panel, 'btn_cleanup'):
            self.view.settings_panel.btn_cleanup.clicked.connect(self.prompt_mod_cleanup)

    def save_config(self):
        self.config_manager.nickname = self.view.settings_panel.input_nick.text() or "Survivor"
        self.config_manager.game_path = self.view.settings_panel.input_path.text()
        if hasattr(self.view.settings_panel, 'input_params'):
            self.config_manager.launch_params = self.view.settings_panel.input_params.text()
        
        
        lang_idx = self.view.settings_panel.combo_lang.currentIndex()
        self.config_manager.language = "uk_UA" if lang_idx == 1 else "en_US"
        
        self.config_manager.save()
        self.server_controller.trigger_apply_local_filters()
        

    def browse_path(self):
        from PyQt6.QtWidgets import QFileDialog
        folder = QFileDialog.getExistingDirectory(self.view, "Select DayZ Folder")
        if folder:
            self.view.settings_panel.input_path.setText(folder)
            self.save_config()
            self.fetch_local_mods()

    def fetch_local_mods(self):
        self.view.tab_mods.table_mods.setRowCount(0)
        if not self.config_manager.game_path: return 
        
        game_path = Path(self.config_manager.game_path)
        workshop_dir = game_path.parents[1] / "workshop" / "content" / "221100"
        
        if workshop_dir.exists():
            watched_dirs = self.mod_watcher.directories()
            if str(workshop_dir) not in watched_dirs:
                if watched_dirs:
                    self.mod_watcher.removePaths(watched_dirs)
                self.mod_watcher.addPath(str(workshop_dir))
        
        worker = ModParserWorker(self.config_manager.game_path)
        worker.setAutoDelete(False)
        worker.signals.finished.connect(self.on_mods_loaded)
        self.active_workers.append(worker)
        self.thread_pool.start(worker)

    def check_downloads(self):
        if not self.mod_controller.downloading_mods:
            self.download_timer.stop()
            return
            
        game_path = Path(self.config_manager.game_path)
        downloads_dir = game_path.parents[1] / "workshop" / "downloads" / "221100"
        content_dir = game_path.parents[1] / "workshop" / "content" / "221100"
        
        finished_any = False
        
        for mod_id in list(self.mod_controller.downloading_mods.keys()):
            dl_path = downloads_dir / str(mod_id)
            content_path = content_dir / str(mod_id)
            
            if content_path.exists() and (content_path / "meta.cpp").exists():
                del self.mod_controller.downloading_mods[mod_id]
                finished_any = True
            elif dl_path.exists():
                total_size = 0
                try:
                    for item in dl_path.rglob('*'):
                        if item.is_file() and not item.is_symlink():
                            total_size += item.stat().st_size
                except OSError:
                    pass
                
                if total_size < 1024:
                    size_str = f"{total_size} B"
                elif total_size < 1024 * 1024:
                    size_str = f"{total_size / 1024:.1f} KB"
                else:
                    mb = total_size / (1024 * 1024)
                    size_str = f"{mb:.1f} MB" if mb < 1024 else f"{mb / 1024:.1f} GB"
                    
                self.mod_controller.downloading_mods[mod_id]["size"] = size_str
                
        if finished_any:
            self.fetch_local_mods()
        else:
            self.mod_controller.update_download_progress()

    def check_existing_downloads(self):
        if not self.config_manager.game_path:
            return
            
        game_path = Path(self.config_manager.game_path)
        downloads_dir = game_path.parents[1] / "workshop" / "downloads" / "221100"
        
        if not downloads_dir.exists():
            return
            
        mod_ids = []
        for item in downloads_dir.iterdir():
            if item.is_dir() and item.name.isdigit():
                mod_id = int(item.name)
                if mod_id not in self.mod_controller.downloading_mods:
                    mod_ids.append(mod_id)
                    
        if not mod_ids:
            return

        import urllib.request, urllib.parse, json
        
        post_data = {'itemcount': len(mod_ids)}
        for i, m_id in enumerate(mod_ids):
            post_data[f'publishedfileids[{i}]'] = m_id
            
        titles = {}
        try:
            url = "https://api.steampowered.com/ISteamRemoteStorage/GetPublishedFileDetails/v1/"
            data = urllib.parse.urlencode(post_data).encode('utf-8')
            req = urllib.request.Request(url, data=data)
            with urllib.request.urlopen(req, timeout=3) as response:
                api_data = json.loads(response.read().decode('utf-8'))
                for detail in api_data.get("response", {}).get("publishedfiledetails", []):
                    if "publishedfileid" in detail and "title" in detail:
                        titles[int(detail["publishedfileid"])] = detail["title"]
        except Exception as e:
            logger.error(f"Error getting mod names from Steam API: {e}", exc_info=True)

        for mod_id in mod_ids:
            mod_name = titles.get(mod_id, f"Mod {mod_id}")
            self.mod_controller.downloading_mods[mod_id] = {"name": mod_name, "size": "0 B"}
            
        self.download_timer.start(500)
        self.mod_controller.render_mods()

    def on_workshop_changed(self, path):
        self.mod_update_timer.start(2000)

    def on_mods_loaded(self, mods_data):
        self.mod_controller.set_mods_data(mods_data)
        if self.pending_launch:
            target_server, action_type = self.pending_launch
            self.pending_launch = None
            self.check_and_launch(target_server, action_type)

    def queue_launch(self, server_data, action_type):
        self.pending_launch = (server_data, action_type)
        self.fetch_local_mods()

    def check_and_launch(self, server_data, action_type):
        server_mods = server_data.get("mods", [])
        local_mod_ids = {str(m.get("published_id")) for m in self.mod_controller.mods_data if m.get("published_id")}
        
        missing_mods = [sm for sm in server_mods if str(sm.get("fileId", sm.get("steamWorkshopId", ""))) and str(sm.get("fileId", sm.get("steamWorkshopId", ""))) not in local_mod_ids]
                
        if missing_mods:
            self.show_missing_mods_dialog(missing_mods, server_data, action_type)
        else:
            GameRunner.launch(self.config_manager, self.mod_controller, server_data, action=action_type)

    def show_missing_mods_dialog(self, missing_mods, server_data, action_type):
        mods_text = "\n".join([m.get("name", m.get("title", self.view.tr("Unknown Mod"))) for m in missing_mods])
        msg = QMessageBox(self.view)
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle(self.view.tr("Missing Mods"))
        msg.setText(self.view.tr("Missing {0} mods for this server. Download them via Steam?").format(len(missing_mods)))
        msg.setDetailedText(mods_text)
        msg.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
        
        if msg.exec() == QMessageBox.StandardButton.Ok:
            mod_ids = []
            for sm in missing_mods:
                raw_id = str(sm.get("fileId", sm.get("steamWorkshopId", "")))
                if raw_id.isdigit():
                    mod_id = int(raw_id)
                    mod_ids.append(mod_id)
                    name = sm.get("name", sm.get("title", "Unknown Mod"))
                    self.mod_controller.downloading_mods[mod_id] = {"name": name, "size": "0 B"}
            
            if mod_ids:
                self.mod_controller.steam_mgr.sync_mods_batch(mod_ids)
                self.mod_controller.render_mods()
                self.download_timer.start(500)
                
            QMessageBox.information(self.view, "Downloading", "Mods added to Steam downloads! Check the Mods tab for progress.")

    def show_about_dialog(self):
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.about(
            self.view,
            self.view.tr("About DMTL"),
            "<h3>DMTL - DayZ MefTeam Launcher</h3>"
            "<p>Custom launcher for DayZ.</p>"
            "<p><a href='https://github.com/69-Lukash/DMTLauncher'>https://github.com/69-Lukash/DMTLauncher</a></p>"
            "<p><b>Credits:</b></p>"
            "<ul>"
            "<li>Thanks to everyone who helped with testing.</li>"
            "<li>Thanks to Kolyakvas for help with the icon.</li>"
            "</ul>"
        )

    def prompt_mod_cleanup(self):
        from PyQt6.QtWidgets import QMessageBox
        
        msg = QMessageBox(self.view)
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle(self.view.tr("Mod Cleanup"))
        msg.setText(self.view.tr("Delete all local mods you are not subscribed to on Steam?"))
        msg.setInformativeText(self.view.tr("This will free up disk space, but you will have to download them again if you join a server that uses them."))
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel)
        
        if msg.exec() == QMessageBox.StandardButton.Yes:
            self.run_mod_cleanup()

    def run_mod_cleanup(self):
        if not self.config_manager.game_path:
            return
            
        from steam.parser import ModCleanupWorker
        
        self.view.settings_panel.btn_cleanup.setEnabled(False)
        self.view.settings_panel.btn_cleanup.setText(self.view.tr("🗑️ Cleaning..."))
        
        worker = ModCleanupWorker(self.config_manager.game_path)
        worker.setAutoDelete(False)
        worker.signals.finished.connect(self.on_cleanup_finished)
        self.active_workers.append(worker)
        self.thread_pool.start(worker)

    def on_cleanup_finished(self, deleted_count):
        from PyQt6.QtWidgets import QMessageBox
        
        self.view.settings_panel.btn_cleanup.setEnabled(True)
        self.view.settings_panel.btn_cleanup.setText(self.view.tr("🗑️ Clean Unsubscribed Mods"))
        
        QMessageBox.information(
            self.view, 
            self.view.tr("Done"), 
            self.view.tr("Successfully deleted {0} orphaned mods.").format(deleted_count)
        )
        
        self.fetch_local_mods()
    
    def show(self):
        self.view.show()