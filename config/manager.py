import json
import os

class ConfigManager:
    def __init__(self, config_path):
        self.config_path = config_path
        self.nickname = "Survivor"
        self.game_path = ""
        self.favorites = []
        self.load()
        self.default_sort = 0

    def load(self):
        if not os.path.exists(self.config_path):
            self.save()
            return

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                self.nickname = config.get("nickname") or "Survivor"
                self.game_path = config.get("game_path", "")
                self.favorites = config.get("favorites", [])
                self.default_sort = config.get("default_sort", 0)
        except (json.JSONDecodeError, IOError):
            print(f"Error reading {self.config_path}. Using defaults.")
            self.save()

    def save(self):
        config = {
            "nickname": self.nickname,
            "game_path": self.game_path,
            "favorites": self.favorites,
            "default_sort": self.default_sort
        }
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4)
        except IOError as e:
            print(f"Error saving config: {e}")

    def add_favorite(self, address):
        if address not in self.favorites:
            self.favorites.append(address)
            self.save()

    def remove_favorite(self, address):
        if address in self.favorites:
            self.favorites.remove(address)
            self.save()

    def get_favorites(self):
        return self.favorites

    def is_favorite(self, address):
        return address in self.favorites


