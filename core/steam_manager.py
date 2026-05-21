import os
import sys
import subprocess

class SteamManager:
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.cmd_script = os.path.join(self.base_dir, "core", "steam_cmd.py")

    def disconnect(self):
        pass

    def _run_steam_cmd(self, action: str, mod_ids: list):
        cmd_args = [str(m) for m in mod_ids]
        
        if sys.platform.startswith("linux"):
            try:
                pid = os.fork()
                if pid > 0:
                    os.waitpid(pid, 0)
                else:
                    # Перша дитина
                    os.setsid()
                    pid2 = os.fork()
                    if pid2 > 0:
                        # Перша дитина миттєво вмирає
                        os._exit(0)
                    else:
                        DEVNULL = os.open(os.devnull, os.O_RDWR)
                        os.dup2(DEVNULL, sys.stdin.fileno())
                        os.dup2(DEVNULL, sys.stdout.fileno())
                        os.dup2(DEVNULL, sys.stderr.fileno())
                        
                        # Запускається скрипт-смертник
                        os.execv(sys.executable, [sys.executable, self.cmd_script, action] + cmd_args)
            except Exception as e:
                print(f"[SteamManager] Fork failed: {e}")
        else:
            try:
                subprocess.Popen(
                    [sys.executable, self.cmd_script, action] + cmd_args,
                    cwd=self.base_dir,
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