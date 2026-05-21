import os
import re
from pathlib import Path
from PyQt6.QtCore import QRunnable, QObject, pyqtSignal

class ModParserSignals(QObject):
    finished = pyqtSignal(list)

class ModParserWorker(QRunnable):
    def __init__(self, game_path):
        super().__init__()
        self.game_path = game_path
        self.signals = ModParserSignals()

    def get_dir_size(self, path):
        total_size = 0
        try:
            for dirpath, _, filenames in os.walk(path, followlinks=True):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    if os.path.exists(fp):
                        total_size += os.path.getsize(fp)
        except OSError:
            pass
        return total_size

    def format_size(self, size_bytes):
        if size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

    def parse_meta(self, mod_path):
        meta_file = mod_path / "meta.cpp"
        mod_file = mod_path / "mod.cpp"
        
        author = "Unknown"
        published_id = ""
        
        if meta_file.exists():
            try:
                content = meta_file.read_text(encoding="utf-8", errors="ignore")
                id_match = re.search(r'publishedid\s*=\s*(\d+)', content, re.IGNORECASE)
                if id_match:
                    published_id = id_match.group(1)
            except Exception:
                pass
                
        if mod_file.exists():
            try:
                content = mod_file.read_text(encoding="utf-8", errors="ignore")
                author_match = re.search(r'author\s*=\s*"([^"]+)"', content, re.IGNORECASE)
                if author_match:
                    author = author_match.group(1)
            except Exception:
                pass
                
        return author, published_id

    def _sync_symlinks(self, workshop_dir: Path):
        steamapps_dir = Path(self.game_path).parents[1]
        content_dir = steamapps_dir / "workshop" / "content" / "221100"
        
        if not content_dir.exists() or not content_dir.is_dir():
            return
            
        if not workshop_dir.exists():
            workshop_dir.mkdir(parents=True, exist_ok=True)
            
        for item in content_dir.iterdir():
            if not item.is_dir() or not item.name.isdigit():
                continue
                
            mod_name = item.name 
            meta_file = item / "meta.cpp"
            
            if meta_file.exists():
                try:
                    content = meta_file.read_text(encoding="utf-8", errors="ignore")
                    name_match = re.search(r'name\s*=\s*"([^"]+)"', content, re.IGNORECASE)
                    if name_match:
                        mod_name = name_match.group(1)
                except Exception:
                    pass
            
            safe_name = "".join(c for c in mod_name if c.isalnum() or c in ("_", "-")).strip()
            symlink_name = f"@{safe_name}"
            symlink_path = workshop_dir / symlink_name
            
            if not symlink_path.exists():
                try:
                    os.symlink(item, symlink_path)
                    print(f"[ModParser] Created symlink for {symlink_name}")
                except OSError as e:
                    print(f"[ModParser] Failed to create symlink {symlink_name}: {e}")

    def run(self):
        mods_list = []
        if not self.game_path:
            self.signals.finished.emit([])
            return

        workshop_path = Path(self.game_path) / "!Workshop"
        
        if workshop_path.exists() and workshop_path.is_dir():
            import shutil
            for item in workshop_path.iterdir():
                try:
                    if item.is_symlink():
                        item.unlink()
                    elif item.is_dir():
                        shutil.rmtree(item)
                except OSError:
                    pass
        
        self._sync_symlinks(workshop_path)
        
        if workshop_path.exists() and workshop_path.is_dir():
            for item in workshop_path.iterdir():
                if item.is_dir() and item.name.startswith("@"):
                    size_bytes = self.get_dir_size(item)
                    author, published_id = self.parse_meta(item)
                    
                    display_name = item.name[1:]
                    
                    mods_list.append({
                        "display_name": display_name,
                        "dir_name": item.name,
                        "author": author,
                        "size": self.format_size(size_bytes),
                        "path": str(item),
                        "published_id": published_id
                    })
                    
        self.signals.finished.emit(mods_list)