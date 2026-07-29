import os
import re
from pathlib import Path
from PyQt6.QtCore import QRunnable, QObject, pyqtSignal
from utils.logger import logger

class ModParserSignals(QObject):
    finished = pyqtSignal(list)

class ModParserWorker(QRunnable):
    def __init__(self, game_path):
        super().__init__()
        self.game_path = Path(game_path)
        self.signals = ModParserSignals()
        self.app_id = "221100"

    def get_dir_size(self, path: Path) -> int:
        total_size = 0
        try:
            for item in path.rglob('*'):
                if item.is_file() and not item.is_symlink():
                    total_size += item.stat().st_size
        except OSError as e:
            logger.debug(f"Failed to read directory size for {path}: {e}")
        return total_size

    def format_size(self, size_bytes: int) -> str:
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
            
        mb = size_bytes / (1024 * 1024)
        if mb < 1024:
            return f"{mb:.1f} MB"
        return f"{mb / 1024:.1f} GB"

    def run(self):
        mods_list = []
        logger.info("Starting local workshop mods parsing")
        try:
            if not str(self.game_path) or not self.game_path.exists():
                logger.warning(f"Game path invalid or does not exist: {self.game_path}")
                self.signals.finished.emit([])
                return

            steamapps_dir = self.game_path.parents[1]
            content_dir = steamapps_dir / "workshop" / "content" / self.app_id

            if not content_dir.exists():
                logger.warning(f"Workshop content dir not found at: {content_dir}")
                self.signals.finished.emit([])
                return

            for item in content_dir.iterdir():
                if not item.is_dir() or not item.name.isdigit():
                    continue

                published_id = item.name
                display_name = published_id
                
                meta_file = item / "meta.cpp"
                if meta_file.exists():
                    try:
                        content = meta_file.read_text(encoding="utf-8", errors="ignore")
                        name_match = re.search(r'name\s*=\s*"([^"]+)"', content, re.IGNORECASE)
                        if name_match:
                            display_name = name_match.group(1)
                    except Exception as e:
                        logger.debug(f"Failed to parse meta.cpp for {item.name}: {e}")

                size_bytes = self.get_dir_size(item)

                mods_list.append({
                    "display_name": display_name,
                    "dir_name": item.name,
                    "author": "Steam",
                    "size": self.format_size(size_bytes),
                    "path": str(item),
                    "published_id": published_id
                })

            logger.info(f"Successfully parsed {len(mods_list)} local mods")
            self.signals.finished.emit(mods_list)
            
        except Exception as e:
            logger.error(f"Critical error while parsing workshop mods: {e}", exc_info=True)
            self.signals.finished.emit([])