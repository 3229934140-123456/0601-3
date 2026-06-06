import click
from datetime import datetime

from esports_cli.context import pass_context
from esports_cli.storage import generate_id
from esports_cli.utils import (
    print_table,
    print_success,
    print_error,
    print_info,
    print_panel,
)


@click.group("match")
def match_cmd():
    """比赛管理：创建、比分录入、地图轮换、对战历史"""
    pass


@match_cmd.command("create")
@click.option("--tournament", "-t", required=True, help="赛事ID")
@click.option("--team-a", "-a", required=True, help="队伍A ID")
@click.option("--team-b", "-b", required=True, help="队伍B ID")
@click.option("--datetime", "-d", "datetime_str", default=None, help="比赛时间")
@click.option("--stage", "-s", default="常规赛", help="比赛阶段")
@click.option("--bo", default=3, help="BO几")
@pass_context
def match_create(ctx, tournament, team_a, team_b, datetime_str, stage, bo):
    """创建新比赛"""
    matches = ctx.db.load_matches()

    if not datetime_str:
        datetime_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    match_id = generate_id("M")
    match_data = {
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
        "mvp": "",
        "duration": "",
        "notes": "",
        "type": "official",
    }

    matches.append(match_data)
    ctx.db.save_matches(matches)
    print_success(f"比赛创建成功: {match_id}")


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
            m.get("datetime", "-"),
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
    """录入比赛总比分"""
    matches = ctx.db.load_matches()

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

    ctx.db.save_matches(matches)
    print_success(f"比分已更新: {score_a} : {score_b}")


@match_cmd.command("map-result")
@click.argument("match_id")
@click.option("--map-name", "-m", required=True, help="地图名称")
@click.option("--score-a", "-a", type=int, required=True, help="队伍A地图比分")
@click.option("--score-b", "-b", type=int, required=True, help="队伍B地图比分")
@click.option("--winner", "-w", required=True, help="胜方: a/b")
@click.option("--duration", "-d", default="", help="地图时长")
@pass_context
def match_map_result(ctx, match_id, map_name, score_a, score_b, winner, duration):
    """录入单张地图结果"""
    matches = ctx.db.load_matches()

    found = False
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
            break

    if not found:
        print_error(f"未找到比赛: {match_id}")
        return

    ctx.db.save_matches(matches)
    print_success(f"地图结果已录入: {map_name} - {score_a} : {score_b}")


@match_cmd.command("finish")
@click.argument("match_id")
@click.option("--mvp", default="", help="MVP选手")
@click.option("--duration", default="", help="总时长")
@pass_context
def match_finish(ctx, match_id, mvp, duration):
    """标记比赛结束"""
    matches = ctx.db.load_matches()

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

    ctx.db.save_matches(matches)
    print_success(f"比赛 {match_id} 已标记为结束")


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
            m.get("date", "-"),
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
    )


@match_cmd.command("status")
@click.argument("match_id")
@click.argument("new_status", type=click.Choice(["scheduled", "live", "finished", "cancelled"]))
@pass_context
def match_set_status(ctx, match_id, new_status):
    """设置比赛状态"""
    matches = ctx.db.load_matches()

    found = False
    for m in matches:
        if m.get("id") == match_id:
            m["status"] = new_status
            found = True
            break

    if not found:
        print_error(f"未找到比赛: {match_id}")
        return

    ctx.db.save_matches(matches)
    status_map = {"scheduled": "未开始", "live": "进行中", "finished": "已结束", "cancelled": "已取消"}
    print_success(f"比赛状态已更新为: {status_map.get(new_status, new_status)}")
