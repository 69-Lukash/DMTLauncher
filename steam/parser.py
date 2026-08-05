from PyQt6.QtCore import QRunnable, QObject, pyqtSignal
import dmtl_core
from utils.logger import logger

class ModParserSignals(QObject):
    finished = pyqtSignal(list)

class ModParserWorker(QRunnable):
    def __init__(self, game_path):
        super().__init__()
        self.game_path = game_path
        self.signals = ModParserSignals()

    def run(self):
        logger.info("Starting local workshop mods parsing via Rust")
        try:
            if not self.game_path:
                self.signals.finished.emit([])
                return
                
            mods_list = dmtl_core.parse_local_mods(self.game_path)
            
            logger.info(f"Successfully parsed {len(mods_list)} local mods")
            self.signals.finished.emit(mods_list)
        except Exception as e:
            logger.error(f"Critical error while parsing workshop mods: {e}", exc_info=True)
            self.signals.finished.emit([])

class ModCleanupSignals(QObject):
    finished = pyqtSignal(int)

class ModCleanupWorker(QRunnable):
    def __init__(self, game_path):
        super().__init__()
        self.game_path = game_path
        self.signals = ModCleanupSignals()

    def run(self):
        logger.info("Starting orphaned mods cleanup via Rust")
        try:
            if not self.game_path:
                self.signals.finished.emit(0)
                return
                
            deleted_count = dmtl_core.clean_orphan_mods(self.game_path)
            
            logger.info(f"Successfully deleted {deleted_count} orphaned mods")
            self.signals.finished.emit(deleted_count)
        except Exception as e:
            logger.error(f"Error during mod cleanup: {e}", exc_info=True)
            self.signals.finished.emit(0)