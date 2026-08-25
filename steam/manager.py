import os
import sys
import subprocess
from utils.logger import logger

class SteamManager:
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.cmd_script = os.path.join(self.base_dir, "steam", "cmd_worker.py")
        self.workers = []

    def disconnect(self):
        for p in self.workers:
            try:
                p.terminate()
            except Exception:
                pass
        self.workers.clear()
        logger.info("Terminated background Steam workers.")
    
    def _run_steam_cmd(self, action: str, mod_ids: list):
        cmd_args = [str(m) for m in mod_ids]
        is_frozen = getattr(sys, 'frozen', False)
        
        if is_frozen:
            exec_args = [sys.executable, action] + cmd_args
            work_dir = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
        else:
            exec_args = [sys.executable, self.cmd_script, action] + cmd_args
            work_dir = self.base_dir

        try:
            if sys.platform == "win32":
                p = subprocess.Popen(
                    exec_args,
                    cwd=work_dir,
                    creationflags=0x00000008 | subprocess.CREATE_NO_WINDOW
                )
            else:
                from utils.paths import get_data_dir
                log_dir = os.path.join(get_data_dir(), "logs")
                os.makedirs(log_dir, exist_ok=True)
                log_path = os.path.join(log_dir, "steam_worker.log")
                with open(log_path, "a") as log_file:
                    p = subprocess.Popen(
                        exec_args,
                        cwd=work_dir,
                        stdout=log_file,
                        stderr=log_file,
                        start_new_session=True
                    )
            self.workers.append(p)
        except Exception as e:
            logger.error(f"Failed to start Steam worker: {e}", exc_info=True)

    def sync_mod(self, mod_id: int):
        logger.info(f"Forcing sync/download for mod {mod_id}...")
        self._run_steam_cmd("sync", [mod_id])

    def sync_mods_batch(self, mod_ids: list):
        logger.info(f"Batch syncing {len(mod_ids)} mods...")
        self._run_steam_cmd("sync", mod_ids)

    def unsubscribe_mod(self, mod_id: int):
        logger.info(f"Unsubscribing from mod {mod_id}")
        self._run_steam_cmd("delete", [mod_id])