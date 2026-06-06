import click
from datetime import datetime, timedelta

from esports_cli.context import pass_context
from esports_cli.storage import generate_id, parse_date
from esports_cli.utils import (
    print_table,
    print_success,
    print_error,
    print_warning,
    print_info,
    format_date,
    format_datetime,
    validate_datetime,
    check_tournament_exists,
    check_team_exists,
    validate_match_for_stage,
    log_operation,
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
            format_datetime(s.get("datetime", "-"), ctx.date_fmt),
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
        table_style=ctx.table_style,
    )
    print_info(f"共 {len(filtered)} 场比赛")


@schedule_cmd.command("add")
@click.option("--tournament", "-t", required=True, help="赛事ID")
@click.option("--team-a", "-a", required=True, help="队伍A ID")
@click.option("--team-b", "-b", required=True, help="队伍B ID")
@click.option("--datetime", "-d", "datetime_str", required=True, help="比赛时间 (YYYY-MM-DD HH:MM)")
@click.option("--stage", "-s", default="", help="比赛阶段（指定时自动校验）")
@click.option("--bo", default=3, type=int, help="BO几")
@pass_context
def schedule_add(ctx, tournament, team_a, team_b, datetime_str, stage, bo):
    """添加赛程（自动同步到比赛记录）"""
    schedules = ctx.db.load_schedules()
    matches = ctx.db.load_matches()
    tournaments = ctx.db.load_tournaments()
    teams = ctx.db.load_teams()

    tour_exists, tour_info = check_tournament_exists(tournaments, tournament)
    if not tour_exists:
        print_error(f"赛事不存在: {tournament}")
        return

    team_a_exists, team_a_info = check_team_exists(teams, team_a)
    if not team_a_exists:
        print_error(f"队伍A不存在: {team_a}")
        return

    team_b_exists, team_b_info = check_team_exists(teams, team_b)
    if not team_b_exists:
        print_error(f"队伍B不存在: {team_b}")
        return

    valid, normalized_dt, date_part = validate_datetime(datetime_str)
    if not valid:
        print_error(f"时间格式不正确: {datetime_str}")
        print_info("请使用格式: YYYY-MM-DD HH:MM 或 YYYY/MM/DD HH:MM")
        return

    if stage:
        valid_stage, stage_err = validate_match_for_stage(
            tour_info, stage, date_part, team_a, team_b
        )
        if not valid_stage:
            print_error(f"阶段校验失败: {stage_err}")
            return

    match_id = generate_id("M")
    schedule = {
        "id": match_id,
        "tournament_id": tournament,
        "team_a_id": team_a,
        "team_b_id": team_b,
        "datetime": normalized_dt,
        "date": date_part,
        "stage": stage,
        "bo": bo,
        "status": "scheduled",
        "score_a": 0,
        "score_b": 0,
        "maps": [],
    }

    schedules.append(schedule)

    match_data = dict(schedule)
    match_data.update({
        "mvp": "",
        "duration": "",
        "notes": "",
        "type": "official",
    })
    matches.append(match_data)

    ctx.db.save_schedules(schedules)
    ctx.db.save_matches(matches)

    settings = ctx.db.load_settings()
    log_operation(ctx.db, settings, "create", "schedule", [match_id],
                  f"{team_a_info.get('name')} vs {team_b_info.get('name')}, BO{bo}, {stage}")

    print_success(f"赛程已添加: {match_id}")
    print_info(f"对阵: {team_a_info.get('name')} vs {team_b_info.get('name')}")
    print_info(f"时间: {normalized_dt}")
    print_info(f"已同步到比赛记录，可使用 match score/map-result 录入结果")


@schedule_cmd.command("edit")
@click.argument("schedule_id")
@click.option("--datetime", "-d", help="比赛时间 (YYYY-MM-DD HH:MM)")
@click.option("--stage", "-s", help="比赛阶段")
@click.option("--bo", type=int, help="BO几")
@click.option("--team-a", help="队伍A ID")
@click.option("--team-b", help="队伍B ID")
@click.option("--tournament", "-t", help="赛事ID")
@pass_context
def schedule_edit(ctx, schedule_id, datetime, stage, bo, team_a, team_b, tournament):
    """修改赛程信息（自动同步到比赛记录）"""
    schedules = ctx.db.load_schedules()
    matches = ctx.db.load_matches()
    teams = ctx.db.load_teams()
    tournaments = ctx.db.load_tournaments()

    sched_data = None
    sched_idx = -1
    for i, s in enumerate(schedules):
        if s.get("id") == schedule_id:
            sched_data = s
            sched_idx = i
            break

    if not sched_data:
        print_error(f"未找到赛程: {schedule_id}")
        return

    teams_map = {t["id"]: t for t in teams}
    tour_map = {t["id"]: t for t in tournaments}

    updates = {}

    if tournament:
        if tournament not in tour_map:
            print_error(f"赛事不存在: {tournament}")
            return
        updates["tournament_id"] = tournament

    if team_a:
        if team_a not in teams_map:
            print_error(f"队伍A不存在: {team_a}")
            return
        updates["team_a_id"] = team_a

    if team_b:
        if team_b not in teams_map:
            print_error(f"队伍B不存在: {team_b}")
            return
        updates["team_b_id"] = team_b

    if datetime:
        valid, normalized_dt, date_part = validate_datetime(datetime)
        if not valid:
            print_error(f"时间格式不正确: {datetime}")
            print_info("请使用格式: YYYY-MM-DD HH:MM 或 YYYY/MM/DD HH:MM")
            return
        updates["datetime"] = normalized_dt
        updates["date"] = date_part

    if stage:
        updates["stage"] = stage

    if bo is not None:
        updates["bo"] = bo

    if not updates:
        print_warning("没有指定任何要修改的字段")
        print_info("可用选项: --datetime, --stage, --bo, --team-a, --team-b, --tournament")
        return

    final_tour_id = updates.get("tournament_id", sched_data.get("tournament_id"))
    final_stage = updates.get("stage", sched_data.get("stage", ""))
    final_date = updates.get("date", sched_data.get("date", ""))
    final_team_a = updates.get("team_a_id", sched_data.get("team_a_id", ""))
    final_team_b = updates.get("team_b_id", sched_data.get("team_b_id", ""))

    if final_stage:
        final_tour = tour_map.get(final_tour_id)
        valid_stage, stage_err = validate_match_for_stage(
            final_tour, final_stage, final_date, final_team_a, final_team_b
        )
        if not valid_stage:
            print_error(f"阶段校验失败: {stage_err}")
            return

    for key, value in updates.items():
        sched_data[key] = value

    schedules[sched_idx] = sched_data
    ctx.db.save_schedules(schedules)

    match_idx = -1
    for i, m in enumerate(matches):
        if m.get("id") == schedule_id:
            match_idx = i
            break

    if match_idx >= 0:
        match_data = matches[match_idx]
        sync_fields = ["tournament_id", "team_a_id", "team_b_id",
                       "datetime", "date", "stage", "bo"]
        for f in sync_fields:
            if f in updates:
                match_data[f] = updates[f]
        matches[match_idx] = match_data
        ctx.db.save_matches(matches)

    settings = ctx.db.load_settings()
    detail_str = ", ".join(f"{k}={v}" for k, v in updates.items())
    log_operation(ctx.db, settings, "edit", "schedule", [schedule_id], detail_str)

    print_success(f"赛程已更新: {schedule_id}")
    for key, value in updates.items():
        print_info(f"  {key}: {value}")
    print_info("已同步更新比赛记录")


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
            format_datetime(s.get("datetime", "-"), ctx.date_fmt),
            f"{team_a} vs {team_b}",
            tour_name,
        ])

    print_table(
        f"即将开始的比赛 (未来{hours}小时)",
        ["比赛ID", "倒计时", "开始时间", "对阵", "赛事"],
        rows,
        table_style=ctx.table_style,
    )
    print_info(f"共 {len(upcoming)} 场比赛即将开始")


@schedule_cmd.command("today")
@pass_context
def schedule_today(ctx):
    """查看今日赛程"""
    today_str = datetime.now().strftime("%Y-%m-%d")
    today_display = format_date(today_str, ctx.date_fmt)
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
        f"今日赛程 ({today_display})",
        ["比赛ID", "时间", "对阵", "赛事", "阶段", "状态"],
        rows,
        table_style=ctx.table_style,
    )
