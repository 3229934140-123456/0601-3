import click
from datetime import datetime, timedelta

from esports_cli.context import pass_context
from esports_cli.storage import generate_id, parse_date
from esports_cli.utils import (
    print_table,
    print_success,
    print_error,
    print_info,
    format_datetime,
)


@click.group("schedule")
def schedule_cmd():
    """赛程管理与查看"""
    pass


@schedule_cmd.command("list")
@click.option("--tournament", "-t", help="赛事ID")
@click.option("--date", "-d", help="指定日期 (YYYY-MM-DD)")
@click.option("--team", "-T", help="队伍ID")
@click.option("--upcoming", "-u", is_flag=True, help="仅显示即将到来的比赛")
@click.option("--past", "-p", is_flag=True, help="仅显示已结束的比赛")
@pass_context
def schedule_list(ctx, tournament, date, team, upcoming, past):
    """查看赛程列表"""
    schedules = ctx.db.load_schedules()
    tournaments = {t["id"]: t for t in ctx.db.load_tournaments()}
    teams = {t["id"]: t for t in ctx.db.load_teams()}

    if not schedules:
        print_info("暂无赛程数据")
        return

    filtered = schedules

    if tournament:
        filtered = [s for s in filtered if s.get("tournament_id") == tournament]

    if date:
        try:
            target_date = parse_date(date)
            filtered = [
                s for s in filtered
                if s.get("date", "").startswith(str(target_date))
            ]
        except ValueError as e:
            print_error(str(e))
            return

    if team:
        filtered = [
            s for s in filtered
            if s.get("team_a_id") == team or s.get("team_b_id") == team
        ]

    now = datetime.now()
    if upcoming:
        filtered = [
            s for s in filtered
            if datetime.strptime(s.get("datetime", "2099-01-01 00:00"), "%Y-%m-%d %H:%M") >= now
        ]
    elif past:
        filtered = [
            s for s in filtered
            if datetime.strptime(s.get("datetime", "1970-01-01 00:00"), "%Y-%m-%d %H:%M") < now
        ]

    filtered.sort(key=lambda x: x.get("datetime", ""))

    rows = []
    for s in filtered:
        tour_name = tournaments.get(s.get("tournament_id", ""), {}).get("name", "-")
        team_a = teams.get(s.get("team_a_id", ""), {}).get("name", "TBD")
        team_b = teams.get(s.get("team_b_id", ""), {}).get("name", "TBD")
        status = s.get("status", "scheduled")
        status_map = {
            "scheduled": "未开始",
            "live": "进行中",
            "finished": "已结束",
            "cancelled": "已取消",
        }
        status_display = status_map.get(status, status)

        rows.append([
            s.get("id", "-"),
            s.get("datetime", "-"),
            tour_name,
            f"{team_a} vs {team_b}",
            s.get("stage", "-"),
            status_display,
        ])

    title = "赛程列表"
    if tournament:
        title += f" - 赛事: {tournament}"
    if date:
        title += f" - 日期: {date}"
    print_table(
        title,
        ["比赛ID", "时间", "赛事", "对阵", "阶段", "状态"],
        rows,
    )
    print_info(f"共 {len(filtered)} 场比赛")


@schedule_cmd.command("add")
@click.option("--tournament", "-t", required=True, help="赛事ID")
@click.option("--team-a", "-a", required=True, help="队伍A ID")
@click.option("--team-b", "-b", required=True, help="队伍B ID")
@click.option("--datetime", "-d", "datetime_str", required=True, help="比赛时间 (YYYY-MM-DD HH:MM)")
@click.option("--stage", "-s", default="常规赛", help="比赛阶段")
@click.option("--bo", default=3, help="BO几")
@pass_context
def schedule_add(ctx, tournament, team_a, team_b, datetime_str, stage, bo):
    """添加赛程"""
    schedules = ctx.db.load_schedules()

    match_id = generate_id("M")
    schedule = {
        "id": match_id,
        "tournament_id": tournament,
        "team_a_id": team_a,
        "team_b_id": team_b,
        "datetime": datetime_str,
        "date": datetime_str.split()[0] if " " in datetime_str else datetime_str,
        "stage": stage,
        "bo": bo,
        "status": "scheduled",
        "score_a": 0,
        "score_b": 0,
        "maps": [],
    }

    schedules.append(schedule)
    ctx.db.save_schedules(schedules)
    print_success(f"赛程已添加: {match_id}")


@schedule_cmd.command("reminders")
@click.option("--hours", "-H", default=24, help="未来多少小时内的提醒")
@pass_context
def schedule_reminders(ctx, hours):
    """查看即将开始的比赛提醒"""
    schedules = ctx.db.load_schedules()
    teams = {t["id"]: t for t in ctx.db.load_teams()}
    tournaments = {t["id"]: t for t in ctx.db.load_tournaments()}

    now = datetime.now()
    end_time = now + timedelta(hours=hours)

    upcoming = []
    for s in schedules:
        if s.get("status") != "scheduled":
            continue
        try:
            match_time = datetime.strptime(s.get("datetime", ""), "%Y-%m-%d %H:%M")
            if now <= match_time <= end_time:
                upcoming.append((match_time, s))
        except ValueError:
            continue

    upcoming.sort(key=lambda x: x[0])

    if not upcoming:
        print_info(f"未来 {hours} 小时内没有比赛")
        return

    rows = []
    for match_time, s in upcoming:
        time_diff = match_time - now
        hours_remaining = int(time_diff.total_seconds() / 3600)
        minutes_remaining = int((time_diff.total_seconds() % 3600) / 60)

        team_a = teams.get(s.get("team_a_id", ""), {}).get("name", "TBD")
        team_b = teams.get(s.get("team_b_id", ""), {}).get("name", "TBD")
        tour_name = tournaments.get(s.get("tournament_id", ""), {}).get("name", "-")

        rows.append([
            s.get("id", "-"),
            f"{hours_remaining}小时{minutes_remaining}分钟后",
            s.get("datetime", "-"),
            f"{team_a} vs {team_b}",
            tour_name,
        ])

    print_table(
        f"即将开始的比赛 (未来{hours}小时)",
        ["比赛ID", "倒计时", "开始时间", "对阵", "赛事"],
        rows,
    )
    print_info(f"共 {len(upcoming)} 场比赛即将开始")


@schedule_cmd.command("today")
@pass_context
def schedule_today(ctx):
    """查看今日赛程"""
    today_str = datetime.now().strftime("%Y-%m-%d")
    schedules = ctx.db.load_schedules()
    teams = {t["id"]: t for t in ctx.db.load_teams()}
    tournaments = {t["id"]: t for t in ctx.db.load_tournaments()}

    today_matches = [
        s for s in schedules
        if s.get("date", "") == today_str
    ]
    today_matches.sort(key=lambda x: x.get("datetime", ""))

    if not today_matches:
        print_info("今日无比赛")
        return

    rows = []
    for s in today_matches:
        team_a = teams.get(s.get("team_a_id", ""), {}).get("name", "TBD")
        team_b = teams.get(s.get("team_b_id", ""), {}).get("name", "TBD")
        tour_name = tournaments.get(s.get("tournament_id", ""), {}).get("name", "-")
        status_map = {"scheduled": "未开始", "live": "进行中", "finished": "已结束"}
        status = status_map.get(s.get("status", "scheduled"), "未知")

        score_str = f" {s.get('score_a', 0)}:{s.get('score_b', 0)}" if s.get("status") != "scheduled" else ""
        rows.append([
            s.get("id", "-"),
            s.get("datetime", "").split()[1] if " " in s.get("datetime", "") else "-",
            f"{team_a} vs {team_b}{score_str}",
            tour_name,
            s.get("stage", "-"),
            status,
        ])

    print_table(
        f"今日赛程 ({today_str})",
        ["比赛ID", "时间", "对阵", "赛事", "阶段", "状态"],
        rows,
    )
