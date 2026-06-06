import click
from rich.table import Table

from esports_cli.context import pass_context
from esports_cli.utils import (
    print_table,
    print_success,
    print_error,
    print_info,
    calculate_win_rate,
    console,
)


@click.group("rank")
def rank_cmd():
    """积分榜与胜率统计"""
    pass


@rank_cmd.command("standings")
@click.option("--tournament", "-t", help="赛事ID")
@click.option("--sort-by", "-s", default="points",
              type=click.Choice(["points", "wins", "win_rate", "net_score"]),
              help="排序方式")
@pass_context
def rank_standings(ctx, tournament, sort_by):
    """查看赛事积分榜"""
    teams = ctx.db.load_teams()
    matches = ctx.db.load_matches()
    tournaments = ctx.db.load_tournaments()

    if tournament:
        tour = next((t for t in tournaments if t.get("id") == tournament), None)
        if not tour:
            print_error(f"未找到赛事: {tournament}")
            return
        tour_teams = tour.get("teams", [])
        team_list = [t for t in teams if t.get("id") in tour_teams]
        tour_name = tour.get("name", tournament)
    else:
        team_list = teams
        tour_name = "所有赛事"

    if not team_list:
        print_info("暂无队伍数据")
        return

    standings = []
    for team in team_list:
        team_id = team.get("id")
        wins = 0
        losses = 0
        points = 0
        score_for = 0
        score_against = 0

        for m in matches:
            if m.get("status") != "finished":
                continue
            if tournament and m.get("tournament_id") != tournament:
                continue

            is_team_a = m.get("team_a_id") == team_id
            is_team_b = m.get("team_b_id") == team_id

            if not (is_team_a or is_team_b):
                continue

            s_a = m.get("score_a", 0)
            s_b = m.get("score_b", 0)

            if is_team_a:
                score_for += s_a
                score_against += s_b
                if s_a > s_b:
                    wins += 1
                    points += 3
                elif s_a < s_b:
                    losses += 1
                else:
                    points += 1
            else:
                score_for += s_b
                score_against += s_a
                if s_b > s_a:
                    wins += 1
                    points += 3
                elif s_b < s_a:
                    losses += 1
                else:
                    points += 1

        net_score = score_for - score_against
        win_rate = calculate_win_rate(wins, losses)

        standings.append({
            "team_id": team_id,
            "team_name": team.get("name", "-"),
            "short_name": team.get("short_name", "-"),
            "wins": wins,
            "losses": losses,
            "points": points,
            "score_for": score_for,
            "score_against": score_against,
            "net_score": net_score,
            "win_rate": win_rate,
            "win_rate_value": (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0,
        })

    sort_keys = {
        "points": lambda x: (-x["points"], -x["wins"], -x["net_score"]),
        "wins": lambda x: (-x["wins"], -x["points"], -x["net_score"]),
        "win_rate": lambda x: (-x["win_rate_value"], -x["wins"], -x["points"]),
        "net_score": lambda x: (-x["net_score"], -x["wins"], -x["points"]),
    }
    standings.sort(key=sort_keys[sort_by])

    rows = []
    for i, s in enumerate(standings, 1):
        rank_tag = ""
        if i == 1:
            rank_tag = "[冠军]"
        elif i == 2:
            rank_tag = "[亚军]"
        elif i == 3:
            rank_tag = "[季军]"

        rank_display = f"{i} {rank_tag}" if rank_tag else str(i)

        rows.append([
            rank_display,
            s["team_name"],
            str(s["wins"]),
            str(s["losses"]),
            s["win_rate"],
            str(s["score_for"]),
            str(s["score_against"]),
            f"{s['net_score']:+d}",
            str(s["points"]),
        ])

    print_table(
        f"积分榜 - {tour_name}",
        ["排名", "队伍", "胜", "负", "胜率", "得分", "失分", "净胜分", "积分"],
        rows,
    )
    print_info(f"共 {len(standings)} 支队伍")


@rank_cmd.command("win-rate")
@click.option("--tournament", "-t", help="赛事ID")
@click.option("--team", "-T", help="队伍ID")
@click.option("--top", "-n", default=10, help="显示前N名")
@pass_context
def rank_win_rate(ctx, tournament, team, top):
    """查看胜率统计"""
    teams = ctx.db.load_teams()
    matches = ctx.db.load_matches()

    team_stats = []

    for t in teams:
        team_id = t.get("id")
        wins = 0
        losses = 0

        for m in matches:
            if m.get("status") != "finished":
                continue
            if tournament and m.get("tournament_id") != tournament:
                continue

            is_team_a = m.get("team_a_id") == team_id
            is_team_b = m.get("team_b_id") == team_id

            if not (is_team_a or is_team_b):
                continue

            s_a = m.get("score_a", 0)
            s_b = m.get("score_b", 0)

            if is_team_a:
                if s_a > s_b:
                    wins += 1
                elif s_a < s_b:
                    losses += 1
            else:
                if s_b > s_a:
                    wins += 1
                elif s_b < s_a:
                    losses += 1

        total = wins + losses
        rate = (wins / total * 100) if total > 0 else 0

        team_stats.append({
            "team_id": team_id,
            "team_name": t.get("name", "-"),
            "wins": wins,
            "losses": losses,
            "total": total,
            "win_rate": f"{rate:.2f}%",
            "win_rate_value": rate,
        })

    team_stats.sort(key=lambda x: (-x["win_rate_value"], -x["wins"]))

    if team:
        team_stats = [s for s in team_stats if s["team_id"] == team]

    team_stats = team_stats[:top]

    if not team_stats:
        print_info("暂无数据")
        return

    max_rate = team_stats[0]["win_rate_value"] if team_stats else 100

    rows = []
    for i, s in enumerate(team_stats, 1):
        bar_length = int((s["win_rate_value"] / max_rate) * 20) if max_rate > 0 else 0
        bar = "█" * bar_length

        rows.append([
            str(i),
            s["team_name"],
            str(s["wins"]),
            str(s["losses"]),
            str(s["total"]),
            s["win_rate"],
            bar,
        ])

    print_table(
        "胜率排行榜",
        ["排名", "队伍", "胜", "负", "总场次", "胜率", "趋势"],
        rows,
    )


@rank_cmd.command("player-stats")
@click.option("--tournament", "-t", help="赛事ID")
@click.option("--team", "-T", help="队伍ID")
@click.option("--sort-by", "-s", default="kda",
              type=click.Choice(["kda", "kills", "deaths", "assists"]),
              help="排序方式")
@click.option("--top", "-n", default=10, help="显示前N名")
@pass_context
def rank_player_stats(ctx, tournament, team, sort_by, top):
    """查看选手数据排行"""
    players = ctx.db.load_players()
    teams = {t["id"]: t for t in ctx.db.load_teams()}

    filtered = players
    if team:
        filtered = [p for p in filtered if p.get("team_id") == team]

    player_list = []
    for p in filtered:
        stats = p.get("stats", {})
        kills = stats.get("kills", 0)
        deaths = stats.get("deaths", 0)
        assists = stats.get("assists", 0)
        kda = (kills + assists) / deaths if deaths > 0 else float(kills + assists)

        player_list.append({
            "player_id": p.get("id"),
            "ingame_id": p.get("ingame_id", "-"),
            "name": p.get("name", "-"),
            "team": teams.get(p.get("team_id", ""), {}).get("name", "自由人"),
            "role": p.get("role", "-"),
            "kills": kills,
            "deaths": deaths,
            "assists": assists,
            "kda": f"{kda:.2f}",
            "kda_value": kda,
        })

    sort_keys = {
        "kda": lambda x: -x["kda_value"],
        "kills": lambda x: -x["kills"],
        "deaths": lambda x: x["deaths"],
        "assists": lambda x: -x["assists"],
    }
    player_list.sort(key=sort_keys[sort_by])
    player_list = player_list[:top]

    if not player_list:
        print_info("暂无选手数据")
        return

    rows = []
    for i, p in enumerate(player_list, 1):
        rows.append([
            str(i),
            p["ingame_id"],
            p["name"],
            p["team"],
            p["role"],
            str(p["kills"]),
            str(p["deaths"]),
            str(p["assists"]),
            p["kda"],
        ])

    print_table(
        "选手数据排行",
        ["排名", "游戏ID", "姓名", "队伍", "角色", "击杀", "死亡", "助攻", "KDA"],
        rows,
    )


@rank_cmd.command("recalculate")
@click.option("--tournament", "-t", help="赛事ID")
@pass_context
def rank_recalculate(ctx, tournament):
    """重新计算积分榜"""
    teams = ctx.db.load_teams()
    matches = ctx.db.load_matches()
    tournaments = ctx.db.load_tournaments()

    for team in teams:
        team_id = team.get("id")
        wins = 0
        losses = 0

        for m in matches:
            if m.get("status") != "finished":
                continue
            if tournament and m.get("tournament_id") != tournament:
                continue

            is_team_a = m.get("team_a_id") == team_id
            is_team_b = m.get("team_b_id") == team_id

            if not (is_team_a or is_team_b):
                continue

            s_a = m.get("score_a", 0)
            s_b = m.get("score_b", 0)

            if is_team_a:
                if s_a > s_b:
                    wins += 1
                elif s_a < s_b:
                    losses += 1
            else:
                if s_b > s_a:
                    wins += 1
                elif s_b < s_a:
                    losses += 1

        if "stats" not in team:
            team["stats"] = {}
        team["stats"]["wins"] = wins
        team["stats"]["losses"] = losses
        team["stats"]["total_matches"] = wins + losses

    ctx.db.save_teams(teams)
    print_success("积分榜已重新计算并更新到队伍数据中")
