import os
import urllib.request, urllib.parse
import json
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QLabel, QMessageBox, QFileDialog
from PyQt6.QtCore import Qt, QThreadPool, QFileSystemWatcher, QTimer, QCoreApplication

from config.manager import ConfigManager
from steam.parser import ModParserWorker
from game.runner import GameRunner
from utils.logger import logger
from utils.paths import get_data_dir
from network.updater import UpdateCheckWorker
from ui.views.main_window import DMTLMainWindow
from ui.controllers.local_controller import LocalController
from ui.controllers.mod_controller import ModController
from ui.controllers.server_controller import ServerController

try:
    from version import __version__ as CURRENT_VERSION
except ImportError:
    CURRENT_VERSION = "dev"

class MainController:
    def __init__(self, config_manager=None):
        self.view = DMTLMainWindow()
        
        self.config_path = self._get_config_path()
        self.config_manager = config_manager or ConfigManager(self.config_path)
        
        old_log = os.path.join(get_data_dir(), "steam_worker.log")
        if os.path.exists(old_log):
            try:
                os.remove(old_log)
            except OSError:
                pass
        
        self.mod_controller = ModController(self.view)
        self.server_controller = ServerController(self.view, self.config_manager, self.queue_launch)
        self.local_controller = LocalController(self.view, self.config_manager, self.mod_controller, self.queue_launch)
        
        self.thread_pool = QThreadPool.globalInstance()
        self.active_workers = []
        self.pending_launch = None
        
        self.mod_watcher = QFileSystemWatcher()
        self.mod_watcher.directoryChanged.connect(self.on_workshop_changed)
        self.dl_update_timer = QTimer()
        self.dl_update_timer.setSingleShot(True)
        self.dl_update_timer.timeout.connect(self.check_downloads)

        self.version_label = QLabel(f"v{CURRENT_VERSION}")
        self.version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.version_label.setObjectName("version_label")
        
        self.version_label.setOpenExternalLinks(True)
        
        layout = self.view.settings_panel.layout()
        layout.insertWidget(layout.count() - 1, self.version_label)

        self.check_for_updates()
        
        self.mod_update_timer = QTimer()
        self.mod_update_timer.setSingleShot(True)
        self.mod_update_timer.timeout.connect(self.fetch_local_mods)
        self.check_existing_downloads()

        self.auto_join_server = None
        self.auto_join_action = None

        self._setup_connections()
        
        self.server_controller.fetch_global_database()
        self.fetch_local_mods()

        self.view.settings_panel.combo_sort.setCurrentIndex(self.config_manager.default_sort)
        self.view.settings_panel.combo_sort.currentIndexChanged.connect(self.save_config)
        
        lang_index = 1 if self.config_manager.language == "uk_UA" else 0
        self.view.settings_panel.combo_lang.setCurrentIndex(lang_index)
        self.view.settings_panel.combo_lang.currentIndexChanged.connect(self.save_config)

    def _get_config_path(self):
        return os.path.join(get_data_dir(), "config.json")

    def _setup_connections(self):
        self.view.settings_panel.input_nick.setText(self.config_manager.nickname)
        self.view.settings_panel.input_path.setText(self.config_manager.game_path)
        self.view.settings_panel.input_nick.editingFinished.connect(self.save_config)
        self.view.settings_panel.input_path.editingFinished.connect(self.save_config)
        self.view.settings_panel.btn_browse.clicked.connect(self.browse_path)

        self.view.settings_panel.label_title.setText(QCoreApplication.translate("MainController", "Settings"))
        self.view.settings_panel.label_nick.setText(QCoreApplication.translate("MainController", "Nickname:"))
        self.view.settings_panel.label_path.setText(QCoreApplication.translate("MainController", "Game Path:"))
        self.view.settings_panel.btn_browse.setText(QCoreApplication.translate("MainController", "Browse"))
        self.view.settings_panel.label_sort.setText(QCoreApplication.translate("MainController", "Sort by:"))
        self.view.settings_panel.combo_sort.setItemText(0, QCoreApplication.translate("MainController", "By Players"))
        self.view.settings_panel.combo_sort.setItemText(1, QCoreApplication.translate("MainController", "By Name (A-Z)"))
        self.view.settings_panel.label_lang.setText(QCoreApplication.translate("MainController", "Language (requires restart):"))
        self.view.settings_panel.label_params.setText(QCoreApplication.translate("MainController", "Launch Parameters:"))

        if hasattr(self.view.settings_panel, 'check_last_played'):
            self.view.settings_panel.check_last_played.setText(QCoreApplication.translate("MainController", "Sort by Last Played"))
            self.view.settings_panel.check_last_played.setChecked(self.config_manager.sort_last_played)
            self.view.settings_panel.check_last_played.stateChanged.connect(self.save_config)
            self.view.settings_panel.check_last_played.stateChanged.connect(self.server_controller.trigger_apply_local_filters)

        if hasattr(self.view.settings_panel, 'btn_cleanup'):
            self.view.settings_panel.btn_cleanup.setText(QCoreApplication.translate("MainController", "🗑️ Clean Unsubscribed Mods"))
                
        if hasattr(self.view.settings_panel, 'btn_about'):
            self.view.settings_panel.btn_about.setText(QCoreApplication.translate("MainController", "About DMTL"))
            
        if hasattr(self.view.settings_panel, 'linux_warning'):
            self.view.settings_panel.linux_warning.setText(QCoreApplication.translate("MainController", "Make sure to force a Steam Play compatibility tool in DayZ properties."))

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
        
        self.config_manager.default_sort = self.view.settings_panel.combo_sort.currentIndex()
        
        lang_idx = self.view.settings_panel.combo_lang.currentIndex()
        self.config_manager.language = "uk_UA" if lang_idx == 1 else "en_US"

        self.config_manager.default_sort = self.view.settings_panel.combo_sort.currentIndex()

        self.config_manager.save()
        self.server_controller.trigger_apply_local_filters()

        if hasattr(self.view.settings_panel, 'check_last_played'):
            self.config_manager.sort_last_played = self.view.settings_panel.check_last_played.isChecked()
        

    def browse_path(self):
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
        downloads_dir = game_path.parents[1] / "workshop" / "downloads" / "221100"
        
        dirs_to_watch = []
        if workshop_dir.exists(): dirs_to_watch.append(str(workshop_dir))
        if downloads_dir.exists(): dirs_to_watch.append(str(downloads_dir))
        
        watched_dirs = self.mod_watcher.directories()
        for d in dirs_to_watch:
            if d not in watched_dirs:
                self.mod_watcher.addPath(d)
        
        worker = ModParserWorker(self.config_manager.game_path)
        worker.setAutoDelete(False)
        worker.signals.finished.connect(
            lambda mods_data, w=worker: self.on_mods_loaded(mods_data, w)
        )
        self.active_workers.append(worker)
        self.thread_pool.start(worker)

    def check_downloads(self):
        if not self.mod_controller.downloading_mods:
            return
            
        game_path = Path(self.config_manager.game_path)
        content_dir = game_path.parents[1] / "workshop" / "content" / "221100"
        downloads_dir = game_path.parents[1] / "workshop" / "downloads" / "221100"
        
        status = {}
        log_path = os.path.join(get_data_dir(), "logs", "steam_worker.log")
        if os.path.exists(log_path):
            try:
                with open(log_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    if lines:
                        for line in reversed(lines):
                            try:
                                status = json.loads(line.strip())
                                break
                            except json.JSONDecodeError:
                                continue
            except Exception as e:
                logger.debug(f"Error reading steam_worker.log: {e}")

        finished_any = False
        
        for mod_id in list(self.mod_controller.downloading_mods.keys()):
            content_path = content_dir / str(mod_id)
            
            if content_path.exists() and (content_path / "meta.cpp").exists():
                del self.mod_controller.downloading_mods[mod_id]
                finished_any = True
            else:
                mod_status = status.get(str(mod_id))
                if mod_status:
                    downloaded = mod_status.get("downloaded", 0)
                    total = mod_status.get("total", 0)
                    
                    if total > 0:
                        percent = int((downloaded / total) * 100)
                        mb_down = downloaded / (1024 * 1024)
                        mb_total = total / (1024 * 1024)
                        size_str = f"{mb_down:.1f}/{mb_total:.1f} MB ({percent}%)"
                    else:
                        target_dir = downloads_dir / str(mod_id)
                        if target_dir.exists():
                            curr_size = sum(f.stat().st_size for f in target_dir.rglob('*') if f.is_file())
                            if curr_size > 0:
                                mb_down = curr_size / (1024 * 1024)
                                size_str = f"⬇️ {mb_down:.1f} MB"
                            else:
                                size_str = "Starting..."
                        else:
                            size_str = "Starting..."
                            
                    self.mod_controller.downloading_mods[mod_id]["size"] = size_str
                
        if finished_any:
            if not self.mod_controller.downloading_mods and self.auto_join_server:
                target = self.auto_join_server
                action = self.auto_join_action
                self.auto_join_server = None
                self.auto_join_action = None
                self.queue_launch(target, action)
            else:
                self.fetch_local_mods()
                if self.mod_controller.downloading_mods:
                    self.dl_update_timer.start(1000)
        else:
            self.mod_controller.update_download_progress()
            self.dl_update_timer.start(1000)

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
            
        self.check_downloads()
        self.mod_controller.render_mods()

    def on_workshop_changed(self, path):
        if "downloads" in path:
            self.dl_update_timer.start(1000)
        else:
            self.mod_update_timer.start(2000)

    def on_mods_loaded(self, mods_data, worker=None):
        if worker and worker in self.active_workers:
            self.active_workers.remove(worker)

        self.mod_controller.set_mods_data(mods_data)
        
        if self.local_controller._list_loaded:
            self.local_controller.load_mods_into_table()

        if self.pending_launch:
            target_server, action_type = self.pending_launch
            self.pending_launch = None
            self.check_and_launch(target_server, action_type)

    def queue_launch(self, server_data, action_type):
        self.pending_launch = (server_data, action_type)
        self.fetch_local_mods()

    def check_and_launch(self, server_data, action_type):
        while QApplication.overrideCursor() is not None: QApplication.restoreOverrideCursor()
        
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
                self.check_downloads()

                self.auto_join_server = server_data
                self.auto_join_action = action_type
                
            title = QCoreApplication.translate("MainController", "Downloading")
            dl_msg = QCoreApplication.translate("MainController", "Mods added to Steam downloads! Check the Mods tab for progress.")
            QMessageBox.information(self.view, title, dl_msg)

    def show_about_dialog(self):
        QMessageBox.about(
            self.view,
            self.view.tr("About DMTL"),
            self.view.tr(
                "<h3>DMTL - DayZ MefTeam Launcher</h3>"
                "<p>Custom launcher for DayZ.</p>"
                "<p><a href='https://github.com/69-Lukash/DMTLauncher'>https://github.com/69-Lukash/DMTLauncher</a></p>"
                "<p><b>Credits:</b></p>"
                "<ul>"
                "<li>Thanks to everyone who helped with testing.</li>"
                "<li>Thanks to Kolyakvas for help with the icon.</li>"
                "</ul>"
            )
        )

    def prompt_mod_cleanup(self):
        
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
        worker.signals.finished.connect(lambda count, w=worker: self.on_cleanup_finished(count, w))
        self.active_workers.append(worker)
        self.thread_pool.start(worker)

    def on_cleanup_finished(self, deleted_count, worker=None):
        if worker and worker in self.active_workers:
            self.active_workers.remove(worker)
        
        self.view.settings_panel.btn_cleanup.setEnabled(True)
        self.view.settings_panel.btn_cleanup.setText(self.view.tr("🗑️ Clean Unsubscribed Mods"))
        
        QMessageBox.information(
            self.view, 
            self.view.tr("Done"), 
            self.view.tr("Successfully deleted {0} orphaned mods.").format(deleted_count)
        )
        
        self.fetch_local_mods()

    def check_for_updates(self):
        worker = UpdateCheckWorker(CURRENT_VERSION)
        worker.setAutoDelete(False)
        worker.signals.update_available.connect(
            lambda ver, url, w=worker: self.show_update_in_settings(ver, url, w)
        )
        self.active_workers.append(worker)
        self.thread_pool.start(worker)

    def show_update_in_settings(self, latest_version, release_url, worker=None):
        if worker and worker in self.active_workers:
            self.active_workers.remove(worker)
            
        html = f'<span class="old-version">v{CURRENT_VERSION}</span> &gt;&gt; <a href="{release_url}" class="new-version">v{latest_version}</a>'
        self.version_label.setText(html)
    
    def show(self):
        self.view.show()