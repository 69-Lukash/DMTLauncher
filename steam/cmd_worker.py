import sys
import os
import time
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from steamworks import STEAMWORKS

def dummy_sub_callback(*args):
    pass

def dummy_unsub_callback(*args):
    pass

def main():
    if len(sys.argv) < 3:
        sys.exit(1)
        
    action = sys.argv[1]
    mod_ids = [int(x) for x in sys.argv[2:] if x.isdigit()]
    
    steam = STEAMWORKS()
    if not steam.initialize():
        sys.exit(1)
        
    steam.Workshop.SetItemSubscribedCallback(dummy_sub_callback)
    steam.Workshop.SetItemUnsubscribedCallback(dummy_unsub_callback)
        
    for mod_id in mod_ids:
        if action == "sync":
            steam.Workshop.SubscribeItem(mod_id)
            if hasattr(steam.Workshop, 'DownloadItem'):
                    steam.Workshop.DownloadItem(mod_id, True)
        elif action == "delete":
            steam.Workshop.UnsubscribeItem(mod_id)
            
    if action == "sync":
        start_time = time.time()
        while time.time() - start_time < 300:
            all_done = True
            status = {}
            for mod_id in mod_ids:
                state = steam.Workshop.GetItemState(mod_id)
                if not (state & 4) or (state & 8) or (state & 16) or (state & 32):
                    all_done = False
                    
                    dl_info = steam.Workshop.GetItemDownloadInfo(mod_id)
                    
                    if dl_info and isinstance(dl_info, (tuple, list)) and len(dl_info) >= 2:
                        downloaded, total = dl_info[0], dl_info[1]
                    else:
                        downloaded, total = 0, 0
                        
                    status[str(mod_id)] = {"downloaded": downloaded, "total": total}
            
            if status:
                print(json.dumps(status), flush=True)
                
            if all_done:
                break
                
            steam.run_callbacks()
            time.sleep(0.5)
    elif action == "delete":
        for _ in range(20):
            steam.run_callbacks()
            time.sleep(0.05)

    os._exit(0)

if __name__ == "__main__":
    main()