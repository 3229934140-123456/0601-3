import os
import sys

if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import click
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from esports_cli.context import pass_context, EsportsCliContext
from esports_cli.commands import (
    config_cmd,
    schedule_cmd,
    match_cmd,
    team_cmd,
    player_cmd,
    rank_cmd,
    report_cmd,
)

console = Console(soft_wrap=False, highlight=False)


@click.group()
@click.version_option(version="1.0.0", prog_name="esports")
@pass_context
def cli(ctx):
    """电子竞技平台命令行工具

    为战队经理和赛事管理员提供快速查询赛事信息的能力。

    支持的命令类别:
      match    比赛管理
      team     队伍管理
      player   选手管理
      schedule 赛程管理
      rank     排名统计
      report   战报与数据
      config   配置与账号
    """
    pass


@cli.command("help")
@click.argument("command", required=False)
@click.pass_context
def help_cmd(ctx, command):
    """显示帮助信息"""
    if command:
        cmd_obj = cli.commands.get(command)
        if cmd_obj:
            click.echo(cmd_obj.get_help(ctx))
        else:
            click.echo(f"未知命令: {command}")
    else:
        click.echo(cli.get_help(ctx))


@cli.command("dashboard")
@pass_context
def dashboard(ctx):
    """显示赛事概览仪表盘"""
    tournaments = ctx.db.load_tournaments()
    teams = ctx.db.load_teams()
    players = ctx.db.load_players()
    matches = ctx.db.load_matches()
    schedules = ctx.db.load_schedules()
    scrims = ctx.db.load_scrims()

    from datetime import datetime, timedelta

    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")

    today_matches = [m for m in schedules if m.get("date") == today_str]
    finished_matches = [m for m in matches if m.get("status") == "finished"]
    live_matches = [m for m in matches if m.get("status") == "live"]

    upcoming_24h = []
    for s in schedules:
        if s.get("status") != "scheduled":
            continue
        try:
            match_time = datetime.strptime(s.get("datetime", ""), "%Y-%m-%d %H:%M")
            if now <= match_time <= now + timedelta(hours=24):
                upcoming_24h.append(s)
        except ValueError:
            continue

    summary_lines = [
        f"当前账号: {ctx.current_account} ({ctx.current_account_info.get('name', '')})",
        f"",
        f"[*] 数据概览:",
        f"    赛事数量: {len(tournaments)}",
        f"    队伍数量: {len(teams)}",
        f"    选手数量: {len(players)}",
        f"    比赛总数: {len(matches)}",
        f"    赛程总数: {len(schedules)}",
        f"    训练赛记录: {len(scrims)}",
        f"",
        f"[#] 今日比赛: {len(today_matches)} 场",
        f"    进行中: {len(live_matches)} 场",
        f"    已结束: {len(finished_matches)} 场",
        f"",
        f"[!] 未来24小时赛程: {len(upcoming_24h)} 场",
    ]

    panel = Panel(
        Text("\n".join(summary_lines)),
        title="电竞平台概览",
        border_style="cyan",
        title_align="left",
    )
    console.print(panel)


cli.add_command(config_cmd)
cli.add_command(schedule_cmd)
cli.add_command(match_cmd)
cli.add_command(team_cmd)
cli.add_command(player_cmd)
cli.add_command(rank_cmd)
cli.add_command(report_cmd)


def main():
    cli()


if __name__ == "__main__":
    main()
