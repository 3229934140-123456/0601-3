import click
from rich.console import Console

from esports_cli.models import db

console = Console()


class EsportsCliContext:
    def __init__(self):
        self.db = db
        self.settings = db.load_settings()

    @property
    def current_account(self):
        return self.settings.get("current_account", "default")

    @property
    def current_account_info(self):
        accounts = self.settings.get("accounts", {})
        return accounts.get(self.current_account, {})

    @property
    def default_tournament(self):
        prefs = self.settings.get("preferences", {})
        return prefs.get("default_tournament", "")

    def save_settings(self):
        self.db.save_settings(self.settings)


pass_context = click.make_pass_decorator(EsportsCliContext, ensure=True)
