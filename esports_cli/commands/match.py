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
@click.option("--stage", "-s", default="常规赛", help="比赛阶段")
@click.option("--bo", default=3, type=int, help="BO几")
@pass_context
def match_create(ctx, tournament, team_a, team_b, datetime_str, stage, bo):
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

    print_success(f"比赛创建成功: {match_id}")
    print_info(f"对阵: {team_a_info.get('name')} vs {team_b_info.get('name')}")
    print_info(f"时间: {normalized_dt}")
    print_info(f"已同步到赛程列表")


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
    for m in matches:
        if m.get("id") == match_id:
            m["score_a"] = score_a
            m["score_b"] = score_b
            if m.get("status") == "scheduled":
                m["status"] = "live"
            if mvp:
                m["mvp"] = mvp
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
    updated_match = None
    for m in matches:
        if m.get("id") == match_id:
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
            updated_match = m
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
