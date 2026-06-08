import subprocess
import time
import sys
import os

class GameRunner:
    @staticmethod
    def launch(config_manager, mod_controller, server_data, action="load"):
        nickname = config_manager.nickname or "Survivor"

        server_mods = server_data.get("mods", [])
        mod_paths = []

        for sm in server_mods:
            mod_id = str(sm.get("fileId", sm.get("steamWorkshopId", "")))
            for local_mod in mod_controller.mods_data:
                if local_mod.get("published_id") == mod_id:
                    mod_paths.append(f"!Workshop/{local_mod['dir_name']}")
                    break

        game_args = [f"-name={nickname}"]

        if mod_paths:
            mods_str = ";".join(mod_paths)
            game_args.append(f"-mod={mods_str}")

        if action == "play" and server_data:
            ip = str(server_data.get("ip", server_data.get("endpoint", {}).get("ip", "")))
            port = str(server_data.get("gamePort", server_data.get("port", server_data.get("endpoint", {}).get("port", ""))))
            if ip and port:
                game_args.extend([f"-connect={ip}", f"-port={port}"])

        if sys.platform == "win32":
            be_exe = os.path.join(config_manager.game_path, "DayZ_BE.exe")
            cmd = [be_exe] + game_args
        else:
            cmd = ["steam", "-applaunch", "221100", "-noLauncher"] + game_args

        print(f"[Runner] Launching: {' '.join(cmd)}")

        mod_controller.steam_mgr.disconnect()
        time.sleep(1.0)

        try:
            flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

            run_dir = config_manager.game_path if config_manager.game_path else None

            subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=flags,
                cwd=run_dir
            )
        except Exception as e:
            with open("launcher_error.log", "w") as f:
                f.write(f"Launch error: {e}")
