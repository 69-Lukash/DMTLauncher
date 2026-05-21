import subprocess
import time

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
        
        cmd = ["steam", "-applaunch", "221100", "-noLauncher", f"-name={nickname}"]
        
        if mod_paths:
            mods_str = ";".join(mod_paths)
            cmd.append(f"-mod={mods_str}")
            
        if action == "play" and server_data:
            ip = str(server_data.get("ip", server_data.get("endpoint", {}).get("ip", "")))
            port = str(server_data.get("port", server_data.get("endpoint", {}).get("port", "")))
            if ip and port:
                cmd.extend([f"+connect={ip}", f"+port={port}"])
                
        print(f"[Runner] Launching: {' '.join(cmd)}")
        
        mod_controller.steam_mgr.disconnect()
        time.sleep(1.0)
        
        try:
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            print(f"[Runner] Failed to launch game: {e}")