def apply_local_filters(all_servers, search_text, map_text, favorites):
    """
    Filters and sorts the list of servers based on search queries and favorite status.
    """
    if not all_servers:
        return []

    query = search_text.strip().lower()
    map_q = map_text.strip().lower()

    filtered = []
    for s in all_servers:
        name = str(s.get("name", "")).lower()
        map_val = str(s.get("map", s.get("mission", ""))).lower()

        if query and query not in name:
            continue
        if map_q and map_q not in map_val:
            continue
        
        filtered.append(s)

    filtered.sort(key=lambda x: int(x.get("players", 0)), reverse=True)
    
    def is_favorite(server_dict):
        ip = str(server_dict.get("ip", server_dict.get("endpoint", {}).get("ip", "")))
        port = str(server_dict.get("port", server_dict.get("endpoint", {}).get("port", 0)))
        address = f"{ip}:{port}"
        return address in favorites
        
    filtered.sort(key=is_favorite, reverse=True)
    
    return filtered
