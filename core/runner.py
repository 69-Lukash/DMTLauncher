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
        
        cmd_args = ["-applaunch", "221100", "-noLauncher", f"-name={nickname}"]
        
        if mod_paths:
            mods_str = ";".join(mod_paths)
            cmd_args.append(f"-mod={mods_str}")
            
        if action == "play" and server_data:
            ip = str(server_data.get("ip", server_data.get("endpoint", {}).get("ip", "")))
            port = str(server_data.get("gamePort", server_data.get("port", server_data.get("endpoint", {}).get("port", ""))))
            if ip and port:
                cmd_args.extend([f"-connect={ip}", f"-port={port}"])
                
        if sys.platform == "win32":
            import winreg
            try:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam")
                steam_exe = winreg.QueryValueEx(key, "SteamExe")[0]
                cmd = [steam_exe] + cmd_args
            except Exception:
                cmd = ["C:\\Program Files (x86)\\Steam\\steam.exe"] + cmd_args
        else:
            cmd = ["steam"] + cmd_args
                
        print(f"[Runner] Launching: {' '.join(cmd)}")
        
        mod_controller.steam_mgr.disconnect()
        time.sleep(1.0)
        
        try:
            flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=flags)
        except Exception as e:
            with open("launcher_error.log", "w") as f:
                f.write(f"Launch error: {e}")