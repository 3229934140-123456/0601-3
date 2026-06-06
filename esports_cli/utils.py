from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from datetime import datetime, date

console = Console()


def create_table(title, columns, show_lines=True, header_style="cyan bold"):
    table = Table(
        title=title,
        show_lines=show_lines,
        header_style=header_style,
        border_style="blue",
        title_style="bold magenta",
    )
    for col in columns:
        if isinstance(col, tuple):
            name, style = col
            table.add_column(name, style=style)
        else:
            table.add_column(col)
    return table


def print_table(title, columns, rows, **kwargs):
    table = create_table(title, columns, **kwargs)
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


def format_date(date_str):
    if isinstance(date_str, (datetime, date)):
        return date_str.strftime("%Y-%m-%d")
    return date_str


def format_datetime(dt_str):
    if isinstance(dt_str, datetime):
        return dt_str.strftime("%Y-%m-%d %H:%M")
    return dt_str


def calculate_win_rate(wins, losses):
    total = wins + losses
    if total == 0:
        return "0.00%"
    rate = (wins / total) * 100
    return f"{rate:.2f}%"
