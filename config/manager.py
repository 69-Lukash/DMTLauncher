import json
import os
from utils.logger import logger

class ConfigManager:
    def __init__(self, config_path):
        self.config_path = config_path
        self.nickname = "Survivor"
        self.game_path = ""
        self.favorites = []
        self.language = "en_US"
        self.default_sort = 0
        logger.debug(f"Initializing ConfigManager with path: {config_path}")
        self.load()

    def load(self):
        if not os.path.exists(self.config_path):
            logger.info(f"Config file not found at {self.config_path}. Creating new one.")
            self.save()
            return

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                self.nickname = config.get("nickname") or "Survivor"
                self.game_path = config.get("game_path", "")
                self.favorites = config.get("favorites", [])
                self.default_sort = config.get("default_sort", 0)
                self.language = config.get("language", "en_US")
            logger.info(f"Successfully loaded config from {self.config_path}")
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Error reading {self.config_path}. Using defaults. Details: {e}")
            self.save()

    def save(self):
        config = {
            "nickname": self.nickname,
            "game_path": self.game_path,
            "favorites": self.favorites,
            "default_sort": self.default_sort,
            "language": self.language
        }
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4)
            logger.debug("Config saved successfully")
        except IOError as e:
            logger.error(f"Error saving config file: {e}", exc_info=True)

    def add_favorite(self, address):
        if address not in self.favorites:
            self.favorites.append(address)
            logger.info(f"Added {address} to favorites")
            self.save()

    def remove_favorite(self, address):
        if address in self.favorites:
            self.favorites.remove(address)
            logger.info(f"Removed {address} from favorites")
            self.save()

    def get_favorites(self):
        return self.favorites

    def is_favorite(self, address):
        return address in self.favorites