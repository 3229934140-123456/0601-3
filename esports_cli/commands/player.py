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


@click.group("player")
def player_cmd():
    """选手管理：资料、禁赛标记"""
    pass


@player_cmd.command("list")
@click.option("--team", "-t", help="队伍ID")
@click.option("--role", "-r", help="角色筛选")
@click.option("--status", "-s", help="状态: active/injured/suspended/benched")
@click.option("--nation", "-n", help="国籍筛选")
@pass_context
def player_list(ctx, team, role, status, nation):
    """查看选手列表"""
    players = ctx.db.load_players()
    teams = {t["id"]: t for t in ctx.db.load_teams()}

    filtered = players

    if team:
        filtered = [p for p in filtered if p.get("team_id") == team]

    if role:
        filtered = [p for p in filtered if p.get("role", "").lower() == role.lower()]

    if status:
        filtered = [p for p in filtered if p.get("status", "") == status]

    if nation:
        filtered = [p for p in filtered if p.get("nationality", "").lower() == nation.lower()]

    if not filtered:
        print_info("暂无选手数据")
        return

    status_map = {
        "active": "活跃",
        "injured": "受伤",
        "suspended": "禁赛",
        "benched": "替补",
        "free_agent": "自由人",
    }

    rows = []
    for p in filtered:
        team_name = teams.get(p.get("team_id", ""), {}).get("name", "自由人")
        status_display = status_map.get(p.get("status", "active"), p.get("status", "-"))
        is_suspended = p.get("status") == "suspended"

        rows.append([
            p.get("id", "-"),
            p.get("ingame_id", "-"),
            p.get("name", "-"),
            team_name,
            p.get("role", "-"),
            status_display,
            p.get("nationality", "-"),
        ])

    print_table(
        "选手列表",
        ["选手ID", "游戏ID", "姓名", "队伍", "角色", "状态", "国籍"],
        rows,
    )
    print_info(f"共 {len(filtered)} 名选手")


@player_cmd.command("info")
@click.argument("player_id")
@pass_context
def player_info(ctx, player_id):
    """查看选手详细资料"""
    players = ctx.db.load_players()
    teams = {t["id"]: t for t in ctx.db.load_teams()}

    player_data = None
    for p in players:
        if p.get("id") == player_id:
            player_data = p
            break

    if not player_data:
        print_error(f"未找到选手: {player_id}")
        return

    team_name = teams.get(player_data.get("team_id", ""), {}).get("name", "自由人")
    status = player_data.get("status", "active")
    status_map = {
        "active": "活跃",
        "injured": "受伤",
        "suspended": "禁赛",
        "benched": "替补",
        "free_agent": "自由人",
    }
    status_display = status_map.get(status, status)

    info_lines = [
        f"选手ID: {player_data.get('id', '-')}",
        f"游戏ID: {player_data.get('ingame_id', '-')}",
        f"姓名: {player_data.get('name', '-')}",
        f"国籍: {player_data.get('nationality', '-')}",
        f"年龄: {player_data.get('age', '-')}",
        f"生日: {player_data.get('birthday', '-')}",
        f"",
        f"队伍: {team_name}",
        f"角色: {player_data.get('role', '-')}",
        f"状态: {status_display}",
        f"加入日期: {player_data.get('join_date', '-')}",
        f"",
        f"个人数据:",
    ]

    stats = player_data.get("stats", {})
    for key, value in stats.items():
        info_lines.append(f"  {key}: {value}")

    if status == "suspended":
        info_lines.append(f"\n禁赛信息:")
        info_lines.append(f"  原因: {player_data.get('suspension_reason', '-')}")
        info_lines.append(f"  开始日期: {player_data.get('suspension_start', '-')}")
        info_lines.append(f"  结束日期: {player_data.get('suspension_end', '-')}")

    if player_data.get("achievements"):
        info_lines.append("\n主要成就:")
        for ach in player_data["achievements"]:
            info_lines.append(f"  • {ach}")

    print_panel(f"选手资料 - {player_data.get('ingame_id', '')}", "\n".join(info_lines))


@player_cmd.command("add")
@click.option("--ingame-id", "-i", required=True, help="游戏ID")
@click.option("--name", "-n", required=True, help="真实姓名")
@click.option("--team", "-t", default="", help="所属队伍ID")
@click.option("--role", "-r", default="", help="角色/位置")
@click.option("--nationality", "-N", default="", help="国籍")
@click.option("--age", type=int, default=0, help="年龄")
@click.option("--birthday", default="", help="生日")
@pass_context
def player_add(ctx, ingame_id, name, team, role, nationality, age, birthday):
    """添加新选手"""
    players = ctx.db.load_players()

    player_id = generate_id("P")
    player_data = {
        "id": player_id,
        "ingame_id": ingame_id,
        "name": name,
        "team_id": team,
        "role": role,
        "status": "active" if team else "free_agent",
        "nationality": nationality,
        "age": age,
        "birthday": birthday,
        "join_date": datetime.now().strftime("%Y-%m-%d") if team else "",
        "stats": {},
        "achievements": [],
    }

    players.append(player_data)
    ctx.db.save_players(players)
    print_success(f"选手添加成功: {ingame_id} (ID: {player_id})")


@player_cmd.command("suspend")
@click.argument("player_id")
@click.option("--reason", "-r", required=True, help="禁赛原因")
@click.option("--start-date", "-s", default="", help="开始日期")
@click.option("--end-date", "-e", default="", help="结束日期")
@pass_context
def player_suspend(ctx, player_id, reason, start_date, end_date):
    """标记选手禁赛"""
    players = ctx.db.load_players()

    found = False
    for p in players:
        if p.get("id") == player_id:
            p["status"] = "suspended"
            p["suspension_reason"] = reason
            p["suspension_start"] = start_date or datetime.now().strftime("%Y-%m-%d")
            p["suspension_end"] = end_date
            found = True
            break

    if not found:
        print_error(f"未找到选手: {player_id}")
        return

    ctx.db.save_players(players)
    print_success(f"选手 {player_id} 已标记为禁赛")
    print_info(f"原因: {reason}")


@player_cmd.command("unsuspend")
@click.argument("player_id")
@pass_context
def player_unsuspend(ctx, player_id):
    """解除选手禁赛"""
    players = ctx.db.load_players()

    found = False
    for p in players:
        if p.get("id") == player_id:
            p["status"] = "active" if p.get("team_id") else "free_agent"
            p["suspension_reason"] = ""
            p["suspension_start"] = ""
            p["suspension_end"] = ""
            found = True
            break

    if not found:
        print_error(f"未找到选手: {player_id}")
        return

    ctx.db.save_players(players)
    print_success(f"选手 {player_id} 已解除禁赛")


@player_cmd.command("status")
@click.argument("player_id")
@click.argument("new_status", type=click.Choice(["active", "injured", "suspended", "benched", "free_agent"]))
@pass_context
def player_set_status(ctx, player_id, new_status):
    """设置选手状态"""
    players = ctx.db.load_players()

    found = False
    for p in players:
        if p.get("id") == player_id:
            p["status"] = new_status
            found = True
            break

    if not found:
        print_error(f"未找到选手: {player_id}")
        return

    ctx.db.save_players(players)
    status_map = {
        "active": "活跃",
        "injured": "受伤",
        "suspended": "禁赛",
        "benched": "替补",
        "free_agent": "自由人",
    }
    print_success(f"选手状态已更新为: {status_map.get(new_status, new_status)}")
