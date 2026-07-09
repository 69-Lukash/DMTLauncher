import os
import sys
import subprocess

class SteamManager:
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.cmd_script = os.path.join(self.base_dir, "steam", "cmd_worker.py")

    def disconnect(self):
        pass

    def _run_steam_cmd(self, action: str, mod_ids: list):
        cmd_args = [str(m) for m in mod_ids]
        is_frozen = getattr(sys, 'frozen', False)
        
        if is_frozen:
            exec_args = [sys.executable, action] + cmd_args
            work_dir = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
        else:
            exec_args = [sys.executable, self.cmd_script, action] + cmd_args
            work_dir = self.base_dir

        if sys.platform.startswith("linux"):
            try:
                pid = os.fork()
                if pid > 0:
                    os.waitpid(pid, 0)
                else:
                    os.setsid()
                    pid2 = os.fork()
                    if pid2 > 0:
                        os._exit(0)
                    else:
                        os.chdir(work_dir)
                        
                        if sys.platform == "win32":
                            app_data = os.getenv('LOCALAPPDATA') or os.getenv('APPDATA')
                            log_dir = os.path.join(app_data, "DMTL")
                        else:
                                from pathlib import Path
                                log_dir = os.path.join(str(Path.home()), ".config", "DMTL")

                        os.makedirs(log_dir, exist_ok=True)
                        log_path = os.path.join(log_dir, "steam_worker.log")
                        log_fd = os.open(log_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
                        
                        os.dup2(log_fd, sys.stdin.fileno())
                        os.dup2(log_fd, sys.stdout.fileno())
                        os.dup2(log_fd, sys.stderr.fileno())
                        
                        os.execv(sys.executable, exec_args)
            except Exception as e:
                print(f"[SteamManager] Fork failed: {e}")
        else:
            try:
                subprocess.Popen(
                    exec_args,
                    cwd=work_dir,
                    creationflags=0x00000008 | subprocess.CREATE_NO_WINDOW
                )
            except Exception as e:
                print(f"[SteamManager] Popen failed: {e}")

    def sync_mod(self, mod_id: int):
        print(f"[SteamManager] Forcing sync/download for mod {mod_id}...")
        self._run_steam_cmd("sync", [mod_id])

    def sync_mods_batch(self, mod_ids: list):
        print(f"[SteamManager] Batch syncing {len(mod_ids)} mods...")
        self._run_steam_cmd("sync", mod_ids)

    def unsubscribe_mod(self, mod_id: int):
        print(f"[SteamManager] Unsubscribing from mod {mod_id}")
        self._run_steam_cmd("delete", [mod_id])
