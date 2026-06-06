from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from datetime import datetime, date

console = Console()


_DATE_FORMAT_MAP = {
    "YYYY-MM-DD": "%Y-%m-%d",
    "YYYY/MM/DD": "%Y/%m/%d",
    "MM-DD": "%m-%d",
    "MM/DD": "%m/%d",
}

_TABLE_STYLES = {
    "rich": {
        "show_lines": True,
        "header_style": "cyan bold",
        "border_style": "blue",
        "title_style": "bold magenta",
    },
    "simple": {
        "show_lines": False,
        "header_style": "bold",
        "border_style": "white",
        "title_style": "bold",
    },
    "grid": {
        "show_lines": True,
        "header_style": "yellow bold",
        "border_style": "green",
        "title_style": "bold cyan",
    },
}


def create_table(title, columns, show_lines=None, header_style=None,
                 border_style=None, title_style=None, table_style=None):
    style_params = _TABLE_STYLES.get(table_style or "rich", _TABLE_STYLES["rich"]).copy()

    if show_lines is not None:
        style_params["show_lines"] = show_lines
    if header_style is not None:
        style_params["header_style"] = header_style
    if border_style is not None:
        style_params["border_style"] = border_style
    if title_style is not None:
        style_params["title_style"] = title_style

    table = Table(
        title=title,
        show_lines=style_params["show_lines"],
        header_style=style_params["header_style"],
        border_style=style_params["border_style"],
        title_style=style_params["title_style"],
    )
    for col in columns:
        if isinstance(col, tuple):
            name, style = col
            table.add_column(name, style=style)
        else:
            table.add_column(col)
    return table


def print_table(title, columns, rows, table_style=None, **kwargs):
    table = create_table(title, columns, table_style=table_style, **kwargs)
    for row in rows:
        table.add_row(*[str(cell) if cell is not None else "-" for cell in row])
    console.print(table)


def print_info(message):
    console.print(f"[cyan]ℹ[/cyan] {message}")


def print_success(message):
    console.print(f"[green]✓[/green] {message}")


def print_warning(message):
    console.print(f"[yellow]⚠[/yellow] {message}")


def print_error(message):
    console.print(f"[red]✗[/red] {message}")


def print_panel(title, content, style="blue"):
    panel = Panel(
        Text(content),
        title=title,
        border_style=style,
        title_align="left",
    )
    console.print(panel)


def format_date(date_str, date_format="YYYY-MM-DD"):
    fmt = _DATE_FORMAT_MAP.get(date_format, "%Y-%m-%d")

    if isinstance(date_str, (datetime, date)):
        dt = date_str
    elif isinstance(date_str, str):
        parsed = None
        for try_fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y-%m-%d %H:%M", "%Y/%m/%d %H:%M"):
            try:
                parsed = datetime.strptime(date_str, try_fmt)
                break
            except ValueError:
                continue
        if not parsed:
            return date_str
        dt = parsed
    else:
        return str(date_str)

    return dt.strftime(fmt)


def format_datetime(dt_str, date_format="YYYY-MM-DD"):
    date_fmt = _DATE_FORMAT_MAP.get(date_format, "%Y-%m-%d")

    if isinstance(dt_str, datetime):
        dt = dt_str
    elif isinstance(dt_str, str):
        try:
            dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
        except ValueError:
            try:
                dt = datetime.strptime(dt_str, "%Y/%m/%d %H:%M")
            except ValueError:
                return dt_str
    else:
        return str(dt_str)

    return f"{dt.strftime(date_fmt)} {dt.strftime('%H:%M')}"


def get_date_format_from_prefs(settings):
    prefs = settings.get("preferences", {})
    return prefs.get("date_format", "YYYY-MM-DD")


def get_table_style_from_prefs(settings):
    prefs = settings.get("preferences", {})
    return prefs.get("table_style", "rich")


def calculate_win_rate(wins, losses):
    total = wins + losses
    if total == 0:
        return "0.00%"
    rate = (wins / total) * 100
    return f"{rate:.2f}%"


def validate_datetime(datetime_str):
    from datetime import datetime

    formats = [
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y/%m/%d %H:%M",
        "%Y/%m/%d %H:%M:%S",
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(datetime_str, fmt)
            normalized = dt.strftime("%Y-%m-%d %H:%M")
            date_part = dt.strftime("%Y-%m-%d")
            return True, normalized, date_part
        except ValueError:
            continue
    return False, None, None


def validate_date(date_str):
    from datetime import datetime

    formats = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%m-%d",
        "%m/%d",
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return True, dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return False, None


def check_tournament_exists(tournaments, tournament_id):
    for t in tournaments:
        if t.get("id") == tournament_id:
            return True, t
    return False, None


def check_team_exists(teams, team_id):
    for t in teams:
        if t.get("id") == team_id:
            return True, t
    return False, None
