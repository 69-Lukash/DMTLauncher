import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from steamworks import STEAMWORKS

def dummy_sub_callback(published_file_id, result):
    pass

def dummy_unsub_callback(published_file_id, result):
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
        elif action == "delete":
            steam.Workshop.UnsubscribeItem(mod_id)
            
    for _ in range(5):
        steam.run_callbacks()
        time.sleep(0.05)

    os._exit(0)

if __name__ == "__main__":
    main()