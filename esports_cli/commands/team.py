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
    calculate_win_rate,
)


@click.group("team")
def team_cmd():
    """队伍管理：档案、阵容、训练赛记录"""
    pass


@team_cmd.command("list")
@click.option("--tournament", "-t", help="赛事ID")
@click.option("--region", "-r", help="地区筛选")
@pass_context
def team_list(ctx, tournament, region):
    """查看队伍列表"""
    teams = ctx.db.load_teams()

    filtered = teams
    if region:
        filtered = [t for t in filtered if t.get("region", "").lower() == region.lower()]

    if tournament:
        tournaments = ctx.db.load_tournaments()
        tour = next((t for t in tournaments if t.get("id") == tournament), None)
        if tour:
            tour_teams = tour.get("teams", [])
            filtered = [t for t in filtered if t.get("id") in tour_teams]
        else:
            print_warning(f"未找到赛事: {tournament}")

    if not filtered:
        print_info("暂无队伍数据")
        return

    rows = []
    for t in filtered:
        wins = t.get("stats", {}).get("wins", 0)
        losses = t.get("stats", {}).get("losses", 0)
        win_rate = calculate_win_rate(wins, losses)

        rows.append([
            t.get("id", "-"),
            t.get("name", "-"),
            t.get("short_name", "-"),
            t.get("region", "-"),
            t.get("coach", "-"),
            str(wins),
            str(losses),
            win_rate,
        ])

    print_table(
        "队伍列表",
        ["队伍ID", "名称", "简称", "地区", "教练", "胜", "负", "胜率"],
        rows,
        table_style=ctx.table_style,
    )
    print_info(f"共 {len(filtered)} 支队伍")


@team_cmd.command("info")
@click.argument("team_id")
@pass_context
def team_info(ctx, team_id):
    """查看队伍档案"""
    teams = ctx.db.load_teams()
    players = ctx.db.load_players()

    team_data = None
    for t in teams:
        if t.get("id") == team_id:
            team_data = t
            break

    if not team_data:
        print_error(f"未找到队伍: {team_id}")
        return

    roster = [p for p in players if p.get("team_id") == team_id]
    active_players = [p for p in roster if p.get("status") != "suspended"]
    suspended_players = [p for p in roster if p.get("status") == "suspended"]

    stats = team_data.get("stats", {})
    wins = stats.get("wins", 0)
    losses = stats.get("losses", 0)
    win_rate = calculate_win_rate(wins, losses)

    info_lines = [
        f"队伍ID: {team_data.get('id', '-')}",
        f"队伍名称: {team_data.get('name', '-')}",
        f"简称: {team_data.get('short_name', '-')}",
        f"地区: {team_data.get('region', '-')}",
        f"成立时间: {team_data.get('founded', '-')}",
        f"",
        f"教练: {team_data.get('coach', '-')}",
        f"经理: {team_data.get('manager', '-')}",
        f"主场: {team_data.get('home_stadium', '-')}",
        f"",
        f"战绩统计:",
        f"  总场次: {wins + losses}",
        f"  胜场: {wins}",
        f"  败场: {losses}",
        f"  胜率: {win_rate}",
        f"",
        f"当前阵容 ({len(active_players)} 人):",
    ]

    for p in active_players:
        role = p.get("role", "-")
        info_lines.append(f"  [{role}] {p.get('name', '-')} (ID: {p.get('id', '-')})")

    if suspended_players:
        info_lines.append(f"\n禁赛选手 ({len(suspended_players)} 人):")
        for p in suspended_players:
            info_lines.append(f"  {p.get('name', '-')} - {p.get('suspension_reason', '')}")

    if team_data.get("achievements"):
        info_lines.append("\n主要成就:")
        for ach in team_data["achievements"]:
            info_lines.append(f"  • {ach}")

    print_panel(f"队伍档案 - {team_data.get('name', '')}", "\n".join(info_lines))


@team_cmd.command("add")
@click.option("--name", "-n", required=True, help="队伍名称")
@click.option("--short-name", "-s", default="", help="队伍简称")
@click.option("--region", "-r", default="", help="地区")
@click.option("--coach", "-c", default="", help="教练")
@click.option("--founded", "-f", default="", help="成立时间")
@pass_context
def team_add(ctx, name, short_name, region, coach, founded):
    """添加新队伍"""
    teams = ctx.db.load_teams()

    team_id = generate_id("T")
    team_data = {
        "id": team_id,
        "name": name,
        "short_name": short_name or name[:3].upper(),
        "region": region,
        "coach": coach,
        "manager": "",
        "home_stadium": "",
        "founded": founded,
        "stats": {
            "wins": 0,
            "losses": 0,
            "total_matches": 0,
        },
        "achievements": [],
        "roster_changes": [],
    }

    teams.append(team_data)
    ctx.db.save_teams(teams)
    print_success(f"队伍添加成功: {name} (ID: {team_id})")


@team_cmd.command("roster-change")
@click.option("--team", "-t", required=True, help="队伍ID")
@click.option("--player", "-p", required=True, help="选手ID")
@click.option("--action", "-a", required=True, type=click.Choice(["join", "leave", "promote", "demote", "loan_in", "loan_out"]),
              help="变更类型")
@click.option("--date", "-d", default="", help="生效日期")
@click.option("--reason", "-r", default="", help="变更原因")
@pass_context
def roster_change(ctx, team, player, action, date, reason):
    """记录阵容变更"""
    teams = ctx.db.load_teams()
    players = ctx.db.load_players()

    team_data = next((t for t in teams if t.get("id") == team), None)
    if not team_data:
        print_error(f"未找到队伍: {team}")
        return

    player_data = next((p for p in players if p.get("id") == player), None)
    if not player_data:
        print_error(f"未找到选手: {player}")
        return

    if not date:
        date = datetime.now().strftime("%Y-%m-%d")

    action_map = {
        "join": "加入",
        "leave": "离开",
        "promote": "晋升",
        "demote": "降级",
        "loan_in": "租借入",
        "loan_out": "租借出",
    }

    if "roster_changes" not in team_data:
        team_data["roster_changes"] = []

    change_record = {
        "date": date,
        "player_id": player,
        "player_name": player_data.get("name", ""),
        "action": action,
        "action_display": action_map.get(action, action),
        "reason": reason,
    }
    team_data["roster_changes"].append(change_record)

    if action in ("join", "promote", "loan_in"):
        player_data["team_id"] = team
    elif action in ("leave", "loan_out"):
        player_data["team_id"] = ""

    ctx.db.save_teams(teams)
    ctx.db.save_players(players)
    print_success(f"阵容变更已记录: {player_data.get('name')} {action_map.get(action, action)} {team_data.get('name')}")


@team_cmd.command("roster-history")
@click.argument("team_id")
@click.option("--limit", "-n", default=20, help="显示数量")
@pass_context
def roster_history(ctx, team_id, limit):
    """查看队伍阵容变更历史"""
    teams = ctx.db.load_teams()

    team_data = next((t for t in teams if t.get("id") == team_id), None)
    if not team_data:
        print_error(f"未找到队伍: {team_id}")
        return

    changes = team_data.get("roster_changes", [])
    changes.sort(key=lambda x: x.get("date", ""), reverse=True)
    changes = changes[:limit]

    if not changes:
        print_info("暂无阵容变更记录")
        return

    rows = []
    for c in changes:
        rows.append([
            format_date(c.get("date", "-"), ctx.date_fmt),
            c.get("player_name", "-"),
            c.get("action_display", c.get("action", "-")),
            c.get("reason", "-"),
        ])

    print_table(
        f"阵容变更历史 - {team_data.get('name', '')}",
        ["日期", "选手", "变更类型", "原因"],
        rows,
        table_style=ctx.table_style,
    )


@team_cmd.group("scrim")
def scrim_cmd():
    """训练赛管理"""
    pass


@scrim_cmd.command("list")
@click.option("--team", "-t", help="队伍ID")
@click.option("--date", "-d", help="日期筛选")
@click.option("--limit", "-n", default=20, help="显示数量")
@pass_context
def scrim_list(ctx, team, date, limit):
    """查看训练赛记录"""
    scrims = ctx.db.load_scrims()
    teams = {t["id"]: t for t in ctx.db.load_teams()}

    filtered = scrims

    if team:
        filtered = [
            s for s in filtered
            if s.get("team_a_id") == team or s.get("team_b_id") == team
        ]

    if date:
        filtered = [s for s in filtered if s.get("date", "").startswith(date)]

    filtered.sort(key=lambda x: x.get("datetime", ""), reverse=True)
    filtered = filtered[:limit]

    if not filtered:
        print_info("暂无训练赛记录")
        return

    rows = []
    for s in filtered:
        team_a = teams.get(s.get("team_a_id", ""), {}).get("name", "-")
        team_b = teams.get(s.get("team_b_id", ""), {}).get("name", "-")
        result = s.get("result", "-")
        result_map = {"win": "胜", "lose": "负", "draw": "平", "pending": "待定"}
        result_display = result_map.get(result, result)

        rows.append([
            s.get("id", "-"),
            format_date(s.get("date", "-"), ctx.date_fmt),
            team_a,
            f"{s.get('score_a', 0)}:{s.get('score_b', 0)}",
            team_b,
            result_display,
            s.get("notes", "")[:20] if s.get("notes") else "-",
        ])

    print_table(
        "训练赛记录",
        ["记录ID", "日期", "队伍A", "比分", "队伍B", "结果", "备注"],
        rows,
        table_style=ctx.table_style,
    )


@scrim_cmd.command("add")
@click.option("--team-a", "-a", required=True, help="我方队伍ID")
@click.option("--team-b", "-b", required=True, help="对手队伍ID")
@click.option("--date", "-d", default="", help="日期 (YYYY-MM-DD)")
@click.option("--score-a", type=int, default=0, help="我方比分")
@click.option("--score-b", type=int, default=0, help="对手比分")
@click.option("--result", "-r", type=click.Choice(["win", "lose", "draw", "pending"]), default="pending", help="结果")
@click.option("--notes", "-n", default="", help="备注")
@pass_context
def scrim_add(ctx, team_a, team_b, date, score_a, score_b, result, notes):
    """添加训练赛记录"""
    scrims = ctx.db.load_scrims()

    if not date:
        date = datetime.now().strftime("%Y-%m-%d")

    scrim_id = generate_id("SCR")
    scrim_data = {
        "id": scrim_id,
        "team_a_id": team_a,
        "team_b_id": team_b,
        "date": date,
        "datetime": f"{date} 00:00",
        "score_a": score_a,
        "score_b": score_b,
        "result": result,
        "notes": notes,
        "maps": [],
    }

    scrims.append(scrim_data)
    ctx.db.save_scrims(scrims)
    print_success(f"训练赛记录已添加: {scrim_id}")
