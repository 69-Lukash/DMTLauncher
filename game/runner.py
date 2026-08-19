import subprocess
import time
import sys
import os
import shlex
from utils.logger import logger

class GameRunner:
    @staticmethod
    def launch(config_manager, mod_controller, server_data, action="load"):
        nickname = config_manager.nickname or "Survivor"
        logger.info(f"Preparing to launch game. Action: {action}, Nickname: {nickname}")

        server_mods = server_data.get("mods", [])
        local_mods = mod_controller.mods_data
        
        mod_paths = []
        for sm in server_mods:
            mod_id = str(sm.get("fileId", sm.get("steamWorkshopId", "")))
            local_mod = next((m for m in local_mods if m.get("published_id") == mod_id), None)
            
            if local_mod and "path" in local_mod:
                mod_path = local_mod["path"]
                
                if sys.platform != "win32":
                    mod_path = "Z:" + mod_path.replace("/", "\\")
                    
                mod_paths.append(mod_path)

        game_args = [f"-name={nickname}"]

        if mod_paths:
            mods_str = ";".join(mod_paths)
            game_args.append(f"-mod={mods_str}")
            logger.debug(f"Loaded {len(mod_paths)} mods for launch")

        if action == "play" and server_data:
            ip = str(server_data.get("ip", ""))
            port = str(server_data.get("gamePort", ""))
            if ip and port:
                game_args.extend([f"-connect={ip}", f"-port={port}"])
                logger.info(f"Connecting directly to {ip}:{port}")

        if hasattr(config_manager, 'launch_params') and config_manager.launch_params:
            extra_args = shlex.split(config_manager.launch_params)
            
            protected_keys = {"-name", "-mod", "-connect", "-port"}
            
            for arg in extra_args:
                arg_key = arg.split('=')[0]
                
                if arg_key in protected_keys:
                    logger.warning(f"Ignored restricted custom param: {arg}")
                    continue
                    
                if arg not in game_args:
                    game_args.append(arg)
                    
            logger.debug(f"Final game_args with custom params: {game_args}")

        if sys.platform == "win32":
            be_exe = os.path.join(config_manager.game_path, "DayZ_BE.exe")
            cmd = [be_exe] + game_args
        else:
            cmd = ["steam", "-applaunch", "221100", "-noLauncher"] + game_args

        logger.info(f"Launch command: {' '.join(cmd)}")

        if hasattr(mod_controller, 'steam_mgr'):
            logger.debug("Disconnecting Steam manager before launch")
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
            logger.info("Game process started successfully")
        except Exception as e:
            logger.error(f"Launch error: Failed to start game process: {e}", exc_info=True)