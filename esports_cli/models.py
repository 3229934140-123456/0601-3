import os
from .storage import get_data_dir, get_config_dir, load_json, save_json


class DataManager:
    def __init__(self):
        self.data_dir = get_data_dir()
        self.config_dir = get_config_dir()
        self._init_files()

    def _init_files(self):
        files = [
            "tournaments.json",
            "teams.json",
            "players.json",
            "matches.json",
            "schedules.json",
            "scrims.json",
            "reminders.json",
        ]
        for f in files:
            filepath = os.path.join(self.data_dir, f)
            if not os.path.exists(filepath):
                save_json(filepath, [])

        config_path = os.path.join(self.config_dir, "settings.json")
        if not os.path.exists(config_path):
            default_settings = {
                "current_account": "default",
                "accounts": {
                    "default": {
                        "name": "默认管理员",
                        "role": "admin",
                        "email": "admin@esports.local",
                    }
                },
                "preferences": {
                    "default_tournament": "",
                    "date_format": "YYYY-MM-DD",
                    "table_style": "rich",
                    "timezone": "Asia/Shanghai",
                },
            }
            save_json(config_path, default_settings)

    def load_tournaments(self):
        return load_json(os.path.join(self.data_dir, "tournaments.json"))

    def save_tournaments(self, data):
        save_json(os.path.join(self.data_dir, "tournaments.json"), data)

    def load_teams(self):
        return load_json(os.path.join(self.data_dir, "teams.json"))

    def save_teams(self, data):
        save_json(os.path.join(self.data_dir, "teams.json"), data)

    def load_players(self):
        return load_json(os.path.join(self.data_dir, "players.json"))

    def save_players(self, data):
        save_json(os.path.join(self.data_dir, "players.json"), data)

    def load_matches(self):
        return load_json(os.path.join(self.data_dir, "matches.json"))

    def save_matches(self, data):
        save_json(os.path.join(self.data_dir, "matches.json"), data)

    def load_schedules(self):
        return load_json(os.path.join(self.data_dir, "schedules.json"))

    def save_schedules(self, data):
        save_json(os.path.join(self.data_dir, "schedules.json"), data)

    def load_scrims(self):
        return load_json(os.path.join(self.data_dir, "scrims.json"))

    def save_scrims(self, data):
        save_json(os.path.join(self.data_dir, "scrims.json"), data)

    def load_reminders(self):
        return load_json(os.path.join(self.data_dir, "reminders.json"))

    def save_reminders(self, data):
        save_json(os.path.join(self.data_dir, "reminders.json"), data)

    def load_settings(self):
        return load_json(os.path.join(self.config_dir, "settings.json"), default={})

    def save_settings(self, data):
        save_json(os.path.join(self.config_dir, "settings.json"), data)


db = DataManager()
