import click
from datetime import datetime

from esports_cli.context import pass_context
from esports_cli.storage import generate_id
from esports_cli.utils import (
    print_table,
    print_success,
    print_error,
    print_warning,
    print_info,
    print_panel,
    format_date,
    format_datetime,
    validate_datetime,
    check_tournament_exists,
    check_team_exists,
    calculate_win_rate,
    validate_match_for_stage,
    log_operation,
    normalize_player_status,
    get_player_status_label,
    is_player_available,
    check_schedule_conflicts,
    scan_all_conflicts,
)


@click.group("match")
def match_cmd():
    """比赛管理：创建、比分录入、地图轮换、对战历史"""
    pass


@match_cmd.command("create")
@click.option("--tournament", "-t", required=True, help="赛事ID")
@click.option("--team-a", "-a", required=True, help="队伍A ID")
@click.option("--team-b", "-b", required=True, help="队伍B ID")
@click.option("--datetime", "-d", "datetime_str", default=None, help="比赛时间 (YYYY-MM-DD HH:MM)")
@click.option("--stage", "-s", default="", help="比赛阶段（指定时自动校验）")
@click.option("--bo", default=3, type=int, help="BO几")
@click.option("--conflict-window", "conflict_window", default=24, type=int,
              help="冲突检测窗口（小时），0 表示全天，默认 24 小时")
@click.option("--force", is_flag=True, help="忽略冲突强制创建")
@pass_context
def match_create(ctx, tournament, team_a, team_b, datetime_str, stage, bo, conflict_window, force):
    """创建新比赛（自动同步到赛程）"""
    matches = ctx.db.load_matches()
    schedules = ctx.db.load_schedules()
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

    if not datetime_str:
        datetime_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    valid, normalized_dt, date_part = validate_datetime(datetime_str)
    if not valid:
        print_error(f"时间格式不正确: {datetime_str}")
        print_info("请使用格式: YYYY-MM-DD HH:MM 或 YYYY/MM/DD HH:MM")
        return

    if stage:
        valid_stage, stage_err = validate_match_for_stage(tour_info, stage, normalized_dt, team_a, team_b)
        if not valid_stage:
            print_error(f"阶段校验失败: {stage_err}")
            return

    if not force:
        conflicts = check_schedule_conflicts(
            matches, team_a, team_b, normalized_dt,
            window_hours=conflict_window
        )
        if conflicts:
            print_warning("检测到赛程冲突:")
            for c in conflicts:
                team_name = team_a_info.get("name") if c["conflict_type"] == "team_a" else team_b_info.get("name")
                print_warning(f"  队伍 {team_name} 与 {c['match_id']} ({c['match_datetime']}) 时间冲突")
            if conflict_window == 0:
                print_warning("（冲突检测范围：全天）")
            else:
                print_warning(f"（冲突检测窗口：{conflict_window} 小时）")
            print_warning("确认要忽略冲突继续创建吗？使用 --force 参数强制创建")
            return

    match_id = generate_id("M")
    match_data = {
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
        "mvp": "",
        "duration": "",
        "notes": "",
        "type": "official",
    }

    matches.append(match_data)

    schedule_data = dict(match_data)
    schedules.append(schedule_data)

    ctx.db.save_matches(matches)
    ctx.db.save_schedules(schedules)

    settings = ctx.db.load_settings()
    log_operation(ctx.db, settings, "create", "match", [match_id],
                  f"{team_a_info.get('name')} vs {team_b_info.get('name')}, BO{bo}, {stage}",
                  after_data=dict(match_data))

    print_success(f"比赛创建成功: {match_id}")
    print_info(f"对阵: {team_a_info.get('name')} vs {team_b_info.get('name')}")
    print_info(f"时间: {normalized_dt}")
    print_info(f"已同步到赛程列表")


@match_cmd.command("edit")
@click.argument("match_id")
@click.option("--datetime", "-d", help="比赛时间 (YYYY-MM-DD HH:MM)")
@click.option("--stage", "-s", help="比赛阶段")
@click.option("--bo", type=int, help="BO几")
@click.option("--team-a", help="队伍A ID")
@click.option("--team-b", help="队伍B ID")
@click.option("--tournament", "-t", help="赛事ID")
@click.option("--conflict-window", "conflict_window", default=24, type=int,
              help="冲突检测窗口（小时），0 表示全天，默认 24 小时")
@click.option("--force", is_flag=True, help="忽略冲突强制修改")
@pass_context
def match_edit(ctx, match_id, datetime, stage, bo, team_a, team_b, tournament, conflict_window, force):
    """修改比赛信息（自动同步到赛程）"""
    matches = ctx.db.load_matches()
    schedules = ctx.db.load_schedules()
    teams = ctx.db.load_teams()
    tournaments = ctx.db.load_tournaments()

    match_data = None
    match_idx = -1
    for i, m in enumerate(matches):
        if m.get("id") == match_id:
            match_data = m
            match_idx = i
            break

    if not match_data:
        print_error(f"未找到比赛: {match_id}")
        return

    before_match = dict(match_data)
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

    final_tour_id = updates.get("tournament_id", match_data.get("tournament_id"))
    final_stage = updates.get("stage", match_data.get("stage", ""))
    final_date = updates.get("date", match_data.get("date", ""))
    final_team_a = updates.get("team_a_id", match_data.get("team_a_id", ""))
    final_team_b = updates.get("team_b_id", match_data.get("team_b_id", ""))

    if final_stage:
        final_tour = tour_map.get(final_tour_id)
        valid_stage, stage_err = validate_match_for_stage(
            final_tour, final_stage, final_date, final_team_a, final_team_b
        )
        if not valid_stage:
            print_error(f"阶段校验失败: {stage_err}")
            return

    needs_conflict_check = (datetime is not None) or (team_a is not None) or (team_b is not None)
    if needs_conflict_check and not force:
        final_dt = updates.get("datetime", match_data.get("datetime", ""))
        conflicts = check_schedule_conflicts(
            matches, final_team_a, final_team_b, final_dt,
            exclude_id=match_id, window_hours=conflict_window
        )
        if conflicts:
            print_warning("检测到赛程冲突:")
            for c in conflicts:
                team_name = teams_map.get(c["team_id"], {}).get("name", c["team_id"])
                print_warning(f"  队伍 {team_name} 与 {c['match_id']} ({c['match_datetime']}) 时间冲突")
            if conflict_window == 0:
                print_warning("（冲突检测范围：全天）")
            else:
                print_warning(f"（冲突检测窗口：{conflict_window} 小时）")
            print_warning("确认要忽略冲突继续修改吗？使用 --force 参数强制修改")
            return

    for key, value in updates.items():
        match_data[key] = value

    matches[match_idx] = match_data
    ctx.db.save_matches(matches)

    sched_idx = -1
    for i, s in enumerate(schedules):
        if s.get("id") == match_id:
            sched_idx = i
            break

    if sched_idx >= 0:
        sched_data = schedules[sched_idx]
        sync_fields = ["tournament_id", "team_a_id", "team_b_id",
                       "datetime", "date", "stage", "bo"]
        for f in sync_fields:
            if f in updates:
                sched_data[f] = updates[f]
        schedules[sched_idx] = sched_data
        ctx.db.save_schedules(schedules)

    settings = ctx.db.load_settings()
    detail_str = ", ".join(f"{k}={v}" for k, v in updates.items())
    log_operation(ctx.db, settings, "edit", "match", [match_id], detail_str,
                  before_data=before_match, after_data=dict(match_data))

    print_success(f"比赛已更新: {match_id}")
    for key, value in updates.items():
        print_info(f"  {key}: {value}")
    print_info("已同步更新赛程")


@match_cmd.command("list")
@click.option("--tournament", "-t", help="赛事ID")
@click.option("--team", "-T", help="队伍ID")
@click.option("--status", "-s", help="状态: scheduled/live/finished/cancelled")
@click.option("--limit", "-n", default=20, help="显示数量")
@pass_context
def match_list(ctx, tournament, team, status, limit):
    """查看比赛列表"""
    matches = ctx.db.load_matches()
    teams = {t["id"]: t for t in ctx.db.load_teams()}
    tournaments = {t["id"]: t for t in ctx.db.load_tournaments()}

    filtered = matches

    if tournament:
        filtered = [m for m in filtered if m.get("tournament_id") == tournament]

    if team:
        filtered = [
            m for m in filtered
            if m.get("team_a_id") == team or m.get("team_b_id") == team
        ]

    if status:
        filtered = [m for m in filtered if m.get("status") == status]

    filtered.sort(key=lambda x: x.get("datetime", ""), reverse=True)
    filtered = filtered[:limit]

    if not filtered:
        print_info("暂无比赛数据")
        return

    rows = []
    status_map = {
        "scheduled": "未开始",
        "live": "进行中",
        "finished": "已结束",
        "cancelled": "已取消",
    }
    for m in filtered:
        team_a = teams.get(m.get("team_a_id", ""), {}).get("name", "TBD")
        team_b = teams.get(m.get("team_b_id", ""), {}).get("name", "TBD")
        tour_name = tournaments.get(m.get("tournament_id", ""), {}).get("name", "-")
        status_display = status_map.get(m.get("status", ""), m.get("status", "-"))
        score = f"{m.get('score_a', 0)} : {m.get('score_b', 0)}" if m.get("status") in ("live", "finished") else "VS"

        rows.append([
            m.get("id", "-"),
            format_datetime(m.get("datetime", "-"), ctx.date_fmt),
            tour_name,
            f"{team_a}",
            score,
            f"{team_b}",
            f"BO{m.get('bo', 3)}",
            status_display,
        ])

    print_table(
        "比赛列表",
        ["比赛ID", "时间", "赛事", "队伍A", "比分", "队伍B", "赛制", "状态"],
        rows,
        table_style=ctx.table_style,
    )
    print_info(f"显示 {len(filtered)} 场比赛")


@match_cmd.command("info")
@click.argument("match_id")
@pass_context
def match_info(ctx, match_id):
    """查看比赛详情"""
    matches = ctx.db.load_matches()
    teams = {t["id"]: t for t in ctx.db.load_teams()}
    tournaments = {t["id"]: t for t in ctx.db.load_tournaments()}

    match_data = None
    for m in matches:
        if m.get("id") == match_id:
            match_data = m
            break

    if not match_data:
        print_error(f"未找到比赛: {match_id}")
        return

    team_a = teams.get(match_data.get("team_a_id", ""), {})
    team_b = teams.get(match_data.get("team_b_id", ""), {})
    tour = tournaments.get(match_data.get("tournament_id", ""), {})

    info_lines = [
        f"比赛ID: {match_data.get('id', '-')}",
        f"赛事: {tour.get('name', '-')}",
        f"阶段: {match_data.get('stage', '-')}",
        f"时间: {match_data.get('datetime', '-')}",
        f"赛制: BO{match_data.get('bo', 3)}",
        f"状态: {match_data.get('status', '-')}",
        f"",
        f"对阵:",
        f"  {team_a.get('name', 'TBD')}  {match_data.get('score_a', 0)} : {match_data.get('score_b', 0)}  {team_b.get('name', 'TBD')}",
        f"",
    ]

    if match_data.get("maps"):
        info_lines.append("地图比分:")
        for i, mp in enumerate(match_data["maps"], 1):
            info_lines.append(f"  地图{i}: {mp.get('map_name', '-')} - "
                            f"{team_a.get('name', 'A')} {mp.get('score_a', 0)} : "
                            f"{mp.get('score_b', 0)} {team_b.get('name', 'B')} "
                            f"(胜者: {mp.get('winner', '-')})")

    if match_data.get("mvp"):
        info_lines.append(f"\nMVP: {match_data['mvp']}")
    if match_data.get("duration"):
        info_lines.append(f"总时长: {match_data['duration']}")

    print_panel(f"比赛详情 - {match_id}", "\n".join(info_lines))


@match_cmd.command("score")
@click.argument("match_id")
@click.option("--score-a", "-a", type=int, required=True, help="队伍A比分")
@click.option("--score-b", "-b", type=int, required=True, help="队伍B比分")
@click.option("--mvp", default="", help="MVP选手")
@pass_context
def match_score(ctx, match_id, score_a, score_b, mvp):
    """录入比赛总比分（自动同步到赛程）"""
    matches = ctx.db.load_matches()
    schedules = ctx.db.load_schedules()

    found = False
    before_match = None
    after_match = None
    for m in matches:
        if m.get("id") == match_id:
            before_match = dict(m)
            m["score_a"] = score_a
            m["score_b"] = score_b
            if m.get("status") == "scheduled":
                m["status"] = "live"
            if mvp:
                m["mvp"] = mvp
            after_match = dict(m)
            found = True
            break

    if not found:
        print_error(f"未找到比赛: {match_id}")
        return

    for s in schedules:
        if s.get("id") == match_id:
            s["score_a"] = score_a
            s["score_b"] = score_b
            if s.get("status") == "scheduled":
                s["status"] = "live"
            if mvp:
                s["mvp"] = mvp
            break

    ctx.db.save_matches(matches)
    ctx.db.save_schedules(schedules)

    settings = ctx.db.load_settings()
    detail = f"比分 {score_a}:{score_b}"
    if mvp:
        detail += f", MVP: {mvp}"
    log_operation(ctx.db, settings, "score_update", "match", [match_id], detail,
                  before_data=before_match, after_data=after_match)

    print_success(f"比分已更新: {score_a} : {score_b}")
    print_info("已同步到赛程列表")


@match_cmd.command("map-result")
@click.argument("match_id")
@click.option("--map-name", "-m", required=True, help="地图名称")
@click.option("--score-a", "-a", type=int, required=True, help="队伍A地图比分")
@click.option("--score-b", "-b", type=int, required=True, help="队伍B地图比分")
@click.option("--winner", "-w", required=True, help="胜方: a/b")
@click.option("--duration", "-d", default="", help="地图时长")
@pass_context
def match_map_result(ctx, match_id, map_name, score_a, score_b, winner, duration):
    """录入单张地图结果（自动同步到赛程）"""
    matches = ctx.db.load_matches()
    schedules = ctx.db.load_schedules()

    found = False
    before_match = None
    updated_match = None
    for m in matches:
        if m.get("id") == match_id:
            before_match = dict(m)
            before_match["maps"] = m.get("maps", [])[:]
            if "maps" not in m:
                m["maps"] = []

            map_data = {
                "map_name": map_name,
                "score_a": score_a,
                "score_b": score_b,
                "winner": winner.upper(),
                "duration": duration,
            }
            m["maps"].append(map_data)

            if winner.lower() == "a":
                m["score_a"] = m.get("score_a", 0) + 1
            else:
                m["score_b"] = m.get("score_b", 0) + 1

            if m.get("status") == "scheduled":
                m["status"] = "live"

            found = True
            updated_match = dict(m)
            updated_match["maps"] = m["maps"][:]
            break

    if not found:
        print_error(f"未找到比赛: {match_id}")
        return

    for s in schedules:
        if s.get("id") == match_id:
            if "maps" not in s:
                s["maps"] = []
            s["maps"].append({
                "map_name": map_name,
                "score_a": score_a,
                "score_b": score_b,
                "winner": winner.upper(),
                "duration": duration,
            })
            if winner.lower() == "a":
                s["score_a"] = s.get("score_a", 0) + 1
            else:
                s["score_b"] = s.get("score_b", 0) + 1
            if s.get("status") == "scheduled":
                s["status"] = "live"
            break

    ctx.db.save_matches(matches)
    ctx.db.save_schedules(schedules)

    settings = ctx.db.load_settings()
    detail = f"地图: {map_name}, 比分 {score_a}:{score_b}, 胜方: {winner.upper()}"
    log_operation(ctx.db, settings, "map_result", "match", [match_id], detail,
                  before_data=before_match, after_data=updated_match)

    print_success(f"地图结果已录入: {map_name} - {score_a} : {score_b}")
    print_info("已同步到赛程列表")


@match_cmd.command("finish")
@click.argument("match_id")
@click.option("--mvp", default="", help="MVP选手")
@click.option("--duration", default="", help="总时长")
@pass_context
def match_finish(ctx, match_id, mvp, duration):
    """标记比赛结束（自动同步到赛程）"""
    matches = ctx.db.load_matches()
    schedules = ctx.db.load_schedules()

    found = False
    for m in matches:
        if m.get("id") == match_id:
            m["status"] = "finished"
            if mvp:
                m["mvp"] = mvp
            if duration:
                m["duration"] = duration
            found = True
            break

    if not found:
        print_error(f"未找到比赛: {match_id}")
        return

    for s in schedules:
        if s.get("id") == match_id:
            s["status"] = "finished"
            if mvp:
                s["mvp"] = mvp
            if duration:
                s["duration"] = duration
            break

    ctx.db.save_matches(matches)
    ctx.db.save_schedules(schedules)
    print_success(f"比赛 {match_id} 已标记为结束")
    print_info("已同步到赛程列表")


@match_cmd.command("history")
@click.argument("team_a")
@click.argument("team_b")
@click.option("--tournament", "-t", help="指定赛事")
@pass_context
def match_history(ctx, team_a, team_b, tournament):
    """查看两支队伍的对战历史"""
    matches = ctx.db.load_matches()
    teams = {t["id"]: t for t in ctx.db.load_teams()}
    tournaments = {t["id"]: t for t in ctx.db.load_tournaments()}

    history = []
    for m in matches:
        ta = m.get("team_a_id")
        tb = m.get("team_b_id")
        if not ((ta == team_a and tb == team_b) or (ta == team_b and tb == team_a)):
            continue
        if tournament and m.get("tournament_id") != tournament:
            continue
        if m.get("status") != "finished":
            continue
        history.append(m)

    history.sort(key=lambda x: x.get("datetime", ""), reverse=True)

    if not history:
        print_info("两支队伍暂无对战历史")
        return

    team_a_name = teams.get(team_a, {}).get("name", team_a)
    team_b_name = teams.get(team_b, {}).get("name", team_b)

    win_a = sum(1 for m in history
                if (m.get("team_a_id") == team_a and m.get("score_a", 0) > m.get("score_b", 0)) or
                   (m.get("team_b_id") == team_a and m.get("score_b", 0) > m.get("score_a", 0)))
    win_b = len(history) - win_a

    print_info(f"对战记录: {team_a_name} 胜 {win_a} 场 / {team_b_name} 胜 {win_b} 场 (共 {len(history)} 场)")

    rows = []
    for m in history:
        ta_name = teams.get(m.get("team_a_id", ""), {}).get("name", "-")
        tb_name = teams.get(m.get("team_b_id", ""), {}).get("name", "-")
        tour_name = tournaments.get(m.get("tournament_id", ""), {}).get("name", "-")

        winner_a = m.get("score_a", 0) > m.get("score_b", 0)
        score_display = f"{m.get('score_a', 0)} : {m.get('score_b', 0)}"

        rows.append([
            m.get("id", "-"),
            format_date(m.get("date", "-"), ctx.date_fmt),
            tour_name,
            m.get("stage", "-"),
            ta_name,
            score_display,
            tb_name,
        ])

    print_table(
        f"对战历史 - {team_a_name} vs {team_b_name}",
        ["比赛ID", "日期", "赛事", "阶段", "队伍A", "比分", "队伍B"],
        rows,
        table_style=ctx.table_style,
    )


@match_cmd.command("status")
@click.argument("match_id")
@click.argument("new_status", type=click.Choice(["scheduled", "live", "finished", "cancelled"]))
@pass_context
def match_set_status(ctx, match_id, new_status):
    """设置比赛状态（自动同步到赛程）"""
    matches = ctx.db.load_matches()
    schedules = ctx.db.load_schedules()

    found = False
    for m in matches:
        if m.get("id") == match_id:
            m["status"] = new_status
            found = True
            break

    if not found:
        print_error(f"未找到比赛: {match_id}")
        return

    for s in schedules:
        if s.get("id") == match_id:
            s["status"] = new_status
            break

    ctx.db.save_matches(matches)
    ctx.db.save_schedules(schedules)
    status_map = {"scheduled": "未开始", "live": "进行中", "finished": "已结束", "cancelled": "已取消"}
    print_success(f"比赛状态已更新为: {status_map.get(new_status, new_status)}")
    print_info("已同步到赛程列表")


@match_cmd.group("tournament")
def tournament_cmd():
    """赛事管理：创建、详情、参赛队伍管理"""
    pass


@tournament_cmd.command("list")
@click.option("--status", "-s", help="状态筛选: scheduled/in_progress/finished")
@pass_context
def tournament_list(ctx, status):
    """查看赛事列表"""
    tournaments = ctx.db.load_tournaments()

    filtered = tournaments
    if status:
        filtered = [t for t in filtered if t.get("status") == status]

    if not filtered:
        print_info("暂无赛事数据")
        return

    rows = []
    status_map = {
        "scheduled": "未开始",
        "in_progress": "进行中",
        "finished": "已结束",
        "cancelled": "已取消",
    }
    for t in filtered:
        team_count = len(t.get("teams", []))
        rows.append([
            t.get("id", "-"),
            t.get("name", "-"),
            t.get("season", "-"),
            str(t.get("year", "-")),
            f"{team_count}支",
            status_map.get(t.get("status", ""), t.get("status", "-")),
            t.get("format", "-"),
        ])

    print_table(
        "赛事列表",
        ["赛事ID", "名称", "赛季", "年份", "参赛队伍", "状态", "赛制"],
        rows,
        table_style=ctx.table_style,
    )
    print_info(f"共 {len(filtered)} 个赛事")


@tournament_cmd.command("info")
@click.argument("tournament_id")
@pass_context
def tournament_info(ctx, tournament_id):
    """查看赛事详情"""
    tournaments = ctx.db.load_tournaments()
    teams_list = ctx.db.load_teams()
    teams_dict = {t["id"]: t for t in teams_list}
    matches = ctx.db.load_matches()

    tour = None
    for t in tournaments:
        if t.get("id") == tournament_id:
            tour = t
            break

    if not tour:
        print_error(f"未找到赛事: {tournament_id}")
        return

    tour_teams = tour.get("teams", [])
    tour_matches = [m for m in matches if m.get("tournament_id") == tournament_id]
    finished_matches = [m for m in tour_matches if m.get("status") == "finished"]

    status_map = {
        "scheduled": "未开始",
        "in_progress": "进行中",
        "finished": "已结束",
        "cancelled": "已取消",
    }

    info_lines = [
        f"赛事ID: {tour.get('id', '-')}",
        f"赛事名称: {tour.get('name', '-')}",
        f"简称: {tour.get('short_name', '-')}",
        f"类型: {tour.get('type', '-')}",
        f"赛季: {tour.get('season', '-')}",
        f"年份: {tour.get('year', '-')}",
        f"状态: {status_map.get(tour.get('status', ''), tour.get('status', '-'))}",
        f"",
        f"开始日期: {tour.get('start_date', '-')}",
        f"结束日期: {tour.get('end_date', '-')}",
        f"赛制: {tour.get('format', '-')}",
        f"奖金池: {tour.get('prize_pool', '-')}",
        f"",
        f"比赛统计:",
        f"  总比赛数: {len(tour_matches)}",
        f"  已结束: {len(finished_matches)}",
        f"  进行中: {len([m for m in tour_matches if m.get('status') == 'live'])}",
        f"  未开始: {len([m for m in tour_matches if m.get('status') == 'scheduled'])}",
        f"",
        f"参赛队伍 ({len(tour_teams)} 支):",
    ]

    for team_id in tour_teams:
        team = teams_dict.get(team_id, {})
        info_lines.append(f"  [{team_id}] {team.get('name', team_id)}")

    if tour.get("description"):
        info_lines.append(f"\n描述: {tour['description']}")

    print_panel(f"赛事详情 - {tour.get('name', '')}", "\n".join(info_lines))


@tournament_cmd.command("create")
@click.option("--id", "tournament_id", required=True, help="赛事ID")
@click.option("--name", "-n", required=True, help="赛事名称")
@click.option("--short-name", "-s", default="", help="简称")
@click.option("--type", "-t", "tour_type", default="regular", help="类型: regular/cup/finals")
@click.option("--season", default="Spring", help="赛季: Spring/Summer/Autumn/Winter/Finals")
@click.option("--year", "-y", default="2024", help="年份")
@click.option("--start-date", default="", help="开始日期")
@click.option("--end-date", default="", help="结束日期")
@click.option("--format", "fmt", default="BO3", help="赛制")
@click.option("--prize-pool", default="", help="奖金池")
@click.option("--description", "-d", default="", help="描述")
@pass_context
def tournament_create(ctx, tournament_id, name, short_name, tour_type, season,
                      year, start_date, end_date, fmt, prize_pool, description):
    """创建新赛事"""
    tournaments = ctx.db.load_tournaments()

    for t in tournaments:
        if t.get("id") == tournament_id:
            print_error(f"赛事ID已存在: {tournament_id}")
            return

    new_tournament = {
        "id": tournament_id,
        "name": name,
        "short_name": short_name or name[:8],
        "type": tour_type,
        "season": season,
        "year": year,
        "start_date": start_date,
        "end_date": end_date,
        "status": "scheduled",
        "teams": [],
        "format": fmt,
        "prize_pool": prize_pool,
        "description": description,
    }

    tournaments.append(new_tournament)
    ctx.db.save_tournaments(tournaments)
    print_success(f"赛事创建成功: {name} (ID: {tournament_id})")


@tournament_cmd.command("add-team")
@click.argument("tournament_id")
@click.argument("team_id")
@pass_context
def tournament_add_team(ctx, tournament_id, team_id):
    """给赛事添加参赛队伍"""
    tournaments = ctx.db.load_tournaments()
    teams = ctx.db.load_teams()

    tour = None
    for t in tournaments:
        if t.get("id") == tournament_id:
            tour = t
            break

    if not tour:
        print_error(f"未找到赛事: {tournament_id}")
        return

    team_exists = False
    team_name = ""
    for tm in teams:
        if tm.get("id") == team_id:
            team_exists = True
            team_name = tm.get("name", "")
            break

    if not team_exists:
        print_error(f"未找到队伍: {team_id}")
        return

    if "teams" not in tour:
        tour["teams"] = []

    if team_id in tour["teams"]:
        print_warning(f"队伍 {team_name} 已在赛事参赛列表中")
        return

    tour["teams"].append(team_id)
    ctx.db.save_tournaments(tournaments)
    print_success(f"队伍 {team_name} 已添加到赛事 {tour.get('name')}")


@tournament_cmd.command("remove-team")
@click.argument("tournament_id")
@click.argument("team_id")
@pass_context
def tournament_remove_team(ctx, tournament_id, team_id):
    """从赛事移除参赛队伍"""
    tournaments = ctx.db.load_tournaments()
    teams = ctx.db.load_teams()

    tour = None
    for t in tournaments:
        if t.get("id") == tournament_id:
            tour = t
            break

    if not tour:
        print_error(f"未找到赛事: {tournament_id}")
        return

    if "teams" not in tour or team_id not in tour["teams"]:
        print_warning(f"队伍 {team_id} 不在赛事参赛列表中")
        return

    tour["teams"].remove(team_id)
    ctx.db.save_tournaments(tournaments)

    team_name = ""
    for tm in teams:
        if tm.get("id") == team_id:
            team_name = tm.get("name", "")
            break

    print_success(f"队伍 {team_name or team_id} 已从赛事 {tour.get('name')} 移除")


@tournament_cmd.command("status")
@click.argument("tournament_id")
@click.argument("new_status", type=click.Choice(["scheduled", "in_progress", "finished", "cancelled"]))
@pass_context
def tournament_set_status(ctx, tournament_id, new_status):
    """设置赛事状态"""
    tournaments = ctx.db.load_tournaments()

    found = False
    for t in tournaments:
        if t.get("id") == tournament_id:
            t["status"] = new_status
            found = True
            break

    if not found:
        print_error(f"未找到赛事: {tournament_id}")
        return

    ctx.db.save_tournaments(tournaments)
    status_map = {
        "scheduled": "未开始",
        "in_progress": "进行中",
        "finished": "已结束",
        "cancelled": "已取消",
    }
    print_success(f"赛事状态已更新为: {status_map.get(new_status, new_status)}")


@tournament_cmd.command("roster")
@click.argument("tournament_id")
@click.option("--region", "-r", help="按地区筛选")
@click.option("--team-status", help="按队伍状态筛选")
@click.option("--available-only", is_flag=True, help="只显示可出场选手")
@click.option("--min-players", type=int, default=5, help="最低出场人数要求")
@pass_context
def tournament_roster(ctx, tournament_id, region, team_status, available_only, min_players):
    """查看赛事参赛名单与选手阵容"""
    tournaments = ctx.db.load_tournaments()
    teams_list = ctx.db.load_teams()
    players = ctx.db.load_players()
    matches = ctx.db.load_matches()

    tour = next((t for t in tournaments if t.get("id") == tournament_id), None)
    if not tour:
        print_error(f"未找到赛事: {tournament_id}")
        return

    tour_team_ids = tour.get("teams", [])
    teams = [t for t in teams_list if t.get("id") in tour_team_ids]

    if region:
        teams = [t for t in teams if t.get("region", "").lower() == region.lower()]

    if team_status:
        teams = [t for t in teams if t.get("status", "") == team_status]

    if not teams:
        print_info("没有符合条件的参赛队伍")
        return

    print_info("")
    print_info(f"参赛队伍: {len(teams)} 支")
    print_info(f"最低出场要求: {min_players} 人")
    print_info("=" * 60)

    for t in teams:
        team_id = t.get("id")
        team_players = [p for p in players if p.get("team_id") == team_id]
        total_players = len(team_players)

        status_counts = {}
        for p in team_players:
            s = normalize_player_status(p.get("status", "active"))
            status_counts[s] = status_counts.get(s, 0) + 1

        active_count = status_counts.get("active", 0)
        substitute_count = status_counts.get("substitute", 0)
        suspended_count = status_counts.get("suspended", 0)
        injured_count = status_counts.get("injured", 0)

        available_count = sum(1 for p in team_players if is_player_available(p.get("status", "active")))
        meets_min = available_count >= min_players

        team_wins = 0
        team_losses = 0
        for m in matches:
            if m.get("status") != "finished":
                continue
            if m.get("tournament_id") != tournament_id:
                continue
            is_a = m.get("team_a_id") == team_id
            is_b = m.get("team_b_id") == team_id
            if not (is_a or is_b):
                continue
            s_a = m.get("score_a", 0)
            s_b = m.get("score_b", 0)
            if is_a:
                if s_a > s_b:
                    team_wins += 1
                elif s_a < s_b:
                    team_losses += 1
            else:
                if s_b > s_a:
                    team_wins += 1
                elif s_b < s_a:
                    team_losses += 1

        form = []
        team_matches = [m for m in matches
                        if m.get("status") == "finished"
                        and m.get("tournament_id") == tournament_id
                        and (m.get("team_a_id") == team_id or m.get("team_b_id") == team_id)]
        team_matches.sort(key=lambda x: x.get("datetime", ""), reverse=True)
        for m in team_matches[:5]:
            is_a = m.get("team_a_id") == team_id
            my_s = m.get("score_a", 0) if is_a else m.get("score_b", 0)
            opp_s = m.get("score_b", 0) if is_a else m.get("score_a", 0)
            form.append("胜" if my_s > opp_s else "负")
        form_str = " ".join(form) if form else "-"

        status_tag = "✓ 满足" if meets_min else "✗ 不满足"
        print_info("")
        print_info(f"【{t.get('name', '')}】 ({t.get('short_name', '')})")
        print_info(f"  地区: {t.get('region', '-')} | 教练: {t.get('coach', '-')}")
        print_info(f"  战绩: {team_wins}胜 {team_losses}负 "
                   f"| 胜率: {calculate_win_rate(team_wins, team_losses)}")
        print_info(f"  近期走势: {form_str}")
        print_info(f"  选手统计: 总计{total_players}人 | "
                   f"正常{active_count} | 替补{substitute_count} | "
                   f"禁赛{suspended_count} | 受伤{injured_count}")
        print_info(f"  可出场: {available_count} 人 最低要求{min_players}人 -> {status_tag}")

        display_players = available_players if available_only else team_players
        if display_players:
            print_info(f"  阵容 ({'可出场' if available_only else '全部'}):")
            for p in display_players[:6]:
                stats = p.get("stats", {})
                kills = stats.get("kills", 0)
                deaths = stats.get("deaths", 0)
                assists = stats.get("assists", 0)
                kda = (kills + assists) / deaths if deaths > 0 else float(kills + assists)
                p_status = get_player_status_label(p.get("status", "active"))
                print_info(f"    {p.get('ingame_id', ''):<10} "
                           f"{p.get('name', ''):<6} "
                           f"{p.get('role', ''):<6} "
                           f"KDA: {kda:.2f} "
                           f"[{p_status}]")
            if len(display_players) > 6:
                print_info(f"    ... 还有 {len(display_players) - 6} 名选手")

    print_info("")
    print_info("=" * 60)


@tournament_cmd.command("stage-list")
@click.argument("tournament_id")
@pass_context
def tournament_stage_list(ctx, tournament_id):
    """查看赛事阶段列表"""
    tournaments = ctx.db.load_tournaments()
    tour = next((t for t in tournaments if t.get("id") == tournament_id), None)
    if not tour:
        print_error(f"未找到赛事: {tournament_id}")
        return

    stages = tour.get("stages", [])

    if not stages:
        print_info("该赛事暂无阶段配置")
        return

    rows = []
    for i, s in enumerate(stages, 1):
        teams = s.get("teams", [])
        team_count = len(teams) if teams else "(继承赛事)"
        points = s.get("points", {})
        points_str = f"胜{points.get('win', 3)} 平{points.get('draw', 1)} 负{points.get('loss', 0)}"
        promotion = s.get("promotion_slots", 0)
        relegation = s.get("relegation_slots", 0)
        rows.append([
            str(i),
            s.get("id", "-"),
            s.get("name", "-"),
            s.get("start_date", "-"),
            s.get("end_date", "-"),
            f"BO{s.get('bo', 3)}",
            str(team_count),
            str(promotion) if promotion else "-",
            str(relegation) if relegation else "-",
            points_str,
        ])

    print_table(
        f"赛事阶段 - {tour.get('name', tournament_id)}",
        ["序号", "阶段ID", "阶段名称", "开始日期", "结束日期", "赛制", "参赛队数", "晋级名额", "淘汰名额", "积分规则"],
        rows,
        table_style=ctx.table_style,
    )


@tournament_cmd.command("stage-add")
@click.argument("tournament_id")
@click.option("--stage-id", required=True, help="阶段ID")
@click.option("--name", required=True, help="阶段名称")
@click.option("--start-date", required=True, help="开始日期 (YYYY-MM-DD)")
@click.option("--end-date", required=True, help="结束日期 (YYYY-MM-DD)")
@click.option("--bo", type=int, default=3, help="赛制")
@click.option("--teams", help="参赛队伍ID列表，逗号分隔；不填则继承赛事全部队伍")
@click.option("--promotion-slots", type=int, default=0, help="晋级名额（前N名晋级下一阶段）")
@click.option("--relegation-slots", type=int, default=0, help="淘汰名额（后N名被淘汰）")
@click.option("--allow-draw/--no-allow-draw", default=False, help="是否允许平局，默认不允许")
@click.option("--points-win", type=int, default=3, help="胜场积分，默认3分")
@click.option("--points-draw", type=int, default=1, help="平局积分，默认1分")
@click.option("--points-loss", type=int, default=0, help="败场积分，默认0分")
@pass_context
def tournament_stage_add(ctx, tournament_id, stage_id, name, start_date, end_date, bo, teams,
                         promotion_slots, relegation_slots, allow_draw, points_win, points_draw, points_loss):
    """添加赛事阶段"""
    from datetime import datetime

    try:
        datetime.strptime(start_date, "%Y-%m-%d")
        datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError:
        print_error("日期格式错误，请使用 YYYY-MM-DD")
        return

    if start_date > end_date:
        print_error("开始日期不能晚于结束日期")
        return

    tournaments = ctx.db.load_tournaments()
    tour = next((t for t in tournaments if t.get("id") == tournament_id), None)
    if not tour:
        print_error(f"未找到赛事: {tournament_id}")
        return

    stages = tour.get("stages", [])
    if any(s.get("id") == stage_id for s in stages):
        print_error(f"阶段ID已存在: {stage_id}")
        return

    tour_teams = set(tour.get("teams", []))
    stage_teams = None
    if teams:
        stage_teams = [t.strip() for t in teams.split(",") if t.strip()]
        all_teams = {t["id"] for t in ctx.db.load_teams()}
        invalid = [t for t in stage_teams if t not in all_teams]
        if invalid:
            print_error(f"以下队伍不存在: {', '.join(invalid)}")
            return
        not_in_tour = [t for t in stage_teams if t not in tour_teams]
        if not_in_tour:
            print_error(f"以下队伍不在参赛名单中: {', '.join(not_in_tour)}")
            return

    new_stage = {
        "id": stage_id,
        "name": name,
        "start_date": start_date,
        "end_date": end_date,
        "bo": bo,
        "promotion_slots": promotion_slots,
        "relegation_slots": relegation_slots,
        "allow_draw": allow_draw,
        "points": {
            "win": points_win,
            "draw": points_draw,
            "loss": points_loss,
        },
    }
    if stage_teams:
        new_stage["teams"] = stage_teams

    stages.append(new_stage)
    tour["stages"] = stages
    ctx.db.save_tournaments(tournaments)

    print_success(f"已添加阶段: {name} ({stage_id})")
    print_info(f"  时间: {start_date} ~ {end_date}")
    print_info(f"  赛制: BO{bo}")
    print_info(f"  积分规则: 胜{points_win}分 平{points_draw}分 负{points_loss}分")
    print_info(f"  平局: {'允许' if allow_draw else '不允许'}")
    print_info(f"  晋级名额: {promotion_slots}")
    print_info(f"  淘汰名额: {relegation_slots}")
    if stage_teams:
        print_info(f"  参赛队伍: {len(stage_teams)} 支")
    else:
        print_info("  参赛队伍: 继承赛事全部队伍")


@tournament_cmd.command("stage-edit")
@click.argument("tournament_id")
@click.argument("stage_id")
@click.option("--name", help="阶段名称")
@click.option("--start-date", help="开始日期")
@click.option("--end-date", help="结束日期")
@click.option("--bo", type=int, help="赛制")
@click.option("--teams", help="参赛队伍ID列表，逗号分隔；传空字符串清除")
@click.option("--promotion-slots", type=int, help="晋级名额")
@click.option("--relegation-slots", type=int, help="淘汰名额")
@click.option("--allow-draw/--no-allow-draw", "allow_draw", default=None, help="是否允许平局")
@click.option("--points-win", type=int, help="胜场积分")
@click.option("--points-draw", type=int, help="平局积分")
@click.option("--points-loss", type=int, help="败场积分")
@pass_context
def tournament_stage_edit(ctx, tournament_id, stage_id, name, start_date, end_date, bo, teams,
                          promotion_slots, relegation_slots, allow_draw, points_win, points_draw, points_loss):
    """修改赛事阶段"""
    from datetime import datetime

    tournaments = ctx.db.load_tournaments()
    tour = next((t for t in tournaments if t.get("id") == tournament_id), None)
    if not tour:
        print_error(f"未找到赛事: {tournament_id}")
        return

    stages = tour.get("stages", [])
    stage = next((s for s in stages if s.get("id") == stage_id), None)
    if not stage:
        print_error(f"未找到阶段: {stage_id}")
        return

    if start_date:
        try:
            datetime.strptime(start_date, "%Y-%m-%d")
        except ValueError:
            print_error("日期格式错误，请使用 YYYY-MM-DD")
            return

    if end_date:
        try:
            datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError:
            print_error("日期格式错误，请使用 YYYY-MM-DD")
            return

    sd = start_date or stage.get("start_date")
    ed = end_date or stage.get("end_date")
    if sd > ed:
        print_error("开始日期不能晚于结束日期")
        return

    tour_teams = set(tour.get("teams", []))
    if teams is not None:
        if teams == "":
            stage.pop("teams", None)
        else:
            stage_teams = [t.strip() for t in teams.split(",") if t.strip()]
            all_teams = {t["id"] for t in ctx.db.load_teams()}
            invalid = [t for t in stage_teams if t not in all_teams]
            if invalid:
                print_error(f"以下队伍不存在: {', '.join(invalid)}")
                return
            not_in_tour = [t for t in stage_teams if t not in tour_teams]
            if not_in_tour:
                print_error(f"以下队伍不在参赛名单中: {', '.join(not_in_tour)}")
                return
            stage["teams"] = stage_teams

    if name:
        stage["name"] = name
    if start_date:
        stage["start_date"] = start_date
    if end_date:
        stage["end_date"] = end_date
    if bo is not None:
        stage["bo"] = bo
    if promotion_slots is not None:
        stage["promotion_slots"] = promotion_slots
    if relegation_slots is not None:
        stage["relegation_slots"] = relegation_slots
    if allow_draw is not None:
        stage["allow_draw"] = allow_draw
    if points_win is not None or points_draw is not None or points_loss is not None:
        points = stage.get("points", {"win": 3, "draw": 1, "loss": 0})
        if points_win is not None:
            points["win"] = points_win
        if points_draw is not None:
            points["draw"] = points_draw
        if points_loss is not None:
            points["loss"] = points_loss
        stage["points"] = points

    ctx.db.save_tournaments(tournaments)
    print_success(f"已更新阶段: {stage.get('name', stage_id)}")


@tournament_cmd.command("stage-remove")
@click.argument("tournament_id")
@click.argument("stage_id")
@pass_context
def tournament_stage_remove(ctx, tournament_id, stage_id):
    """删除赛事阶段"""
    tournaments = ctx.db.load_tournaments()
    tour = next((t for t in tournaments if t.get("id") == tournament_id), None)
    if not tour:
        print_error(f"未找到赛事: {tournament_id}")
        return

    stages = tour.get("stages", [])
    stage = next((s for s in stages if s.get("id") == stage_id), None)
    if not stage:
        print_error(f"未找到阶段: {stage_id}")
        return

    stages[:] = [s for s in stages if s.get("id") != stage_id]
    tour["stages"] = stages
    ctx.db.save_tournaments(tournaments)
    print_success(f"已删除阶段: {stage.get('name', stage_id)}")
