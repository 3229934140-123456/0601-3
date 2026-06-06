import click
import os
import json
from datetime import datetime
from pathlib import Path

from esports_cli.context import pass_context
from esports_cli.utils import (
    print_table,
    print_success,
    print_error,
    print_warning,
    print_info,
    print_panel,
    format_date,
    format_datetime,
    calculate_win_rate,
    validate_datetime,
    console,
    log_operation,
    normalize_player_status,
    get_player_status_label,
    is_player_available,
)


@click.group("report")
def report_cmd():
    """战报导出与数据筛选"""
    pass


@report_cmd.command("match")
@click.argument("match_id")
@click.option("--format", "-f", "output_format", default="text",
              type=click.Choice(["text", "md", "json"]),
              help="输出格式")
@click.option("--compare-depth", "-d", default="3",
              type=click.Choice(["3", "5", "all"]),
              help="核心选手对比数量：3人/5人/全部首发")
@click.option("--output", "-o", default="", help="输出文件路径")
@pass_context
def report_match(ctx, match_id, output_format, compare_depth, output):
    """生成单场比赛战报"""
    matches = ctx.db.load_matches()
    teams_list = ctx.db.load_teams()
    teams = {t["id"]: t for t in teams_list}
    tournaments = {t["id"]: t for t in ctx.db.load_tournaments()}
    players = ctx.db.load_players()

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

    h2h_matches = []
    ta_id = match_data.get("team_a_id")
    tb_id = match_data.get("team_b_id")
    for m in matches:
        if m.get("status") != "finished":
            continue
        if m.get("id") == match_id:
            continue
        ma = m.get("team_a_id")
        mb = m.get("team_b_id")
        if (ma == ta_id and mb == tb_id) or (ma == tb_id and mb == ta_id):
            h2h_matches.append(m)
    h2h_matches.sort(key=lambda x: x.get("datetime", ""), reverse=True)

    h2h_wins_a = sum(1 for m in h2h_matches
                     if (m.get("team_a_id") == ta_id and m.get("score_a", 0) > m.get("score_b", 0)) or
                        (m.get("team_b_id") == ta_id and m.get("score_b", 0) > m.get("score_a", 0)))
    h2h_wins_b = len(h2h_matches) - h2h_wins_a

    def get_team_players(team_id):
        return [p for p in players if p.get("team_id") == team_id
                and p.get("status") != "suspended"]

    def get_core_players(team_id):
        ps = get_team_players(team_id)
        ps.sort(key=lambda p: -(p.get("stats", {}).get("kills", 0)
                                  + p.get("stats", {}).get("assists", 0)))
        if compare_depth == "all":
            return ps
        return ps[:int(compare_depth)]

    team_a_players = get_team_players(ta_id)
    team_b_players = get_team_players(tb_id)
    team_a_core = get_core_players(ta_id)
    team_b_core = get_core_players(tb_id)

    def get_recent_form(team_id, n=5):
        team_matches = []
        for m in matches:
            if m.get("status") != "finished":
                continue
            if m.get("team_a_id") != team_id and m.get("team_b_id") != team_id:
                continue
            team_matches.append(m)
        team_matches.sort(key=lambda x: x.get("datetime", ""), reverse=True)
        results = []
        wins = 0
        for m in team_matches[:n]:
            is_a = m.get("team_a_id") == team_id
            s_a = m.get("score_a", 0)
            s_b = m.get("score_b", 0)
            if is_a:
                w = s_a > s_b
            else:
                w = s_b > s_a
            if w:
                wins += 1
                results.append({"result": "胜", "score": f"{s_a}:{s_b}" if is_a else f"{s_b}:{s_a}",
                                "opponent": m.get("team_b_id") if is_a else m.get("team_a_id"),
                                "date": m.get("date", "")})
            else:
                results.append({"result": "负", "score": f"{s_a}:{s_b}" if is_a else f"{s_b}:{s_a}",
                                "opponent": m.get("team_b_id") if is_a else m.get("team_a_id"),
                                "date": m.get("date", "")})
        return results, wins

    team_a_form, team_a_recent_wins = get_recent_form(ta_id)
    team_b_form, team_b_recent_wins = get_recent_form(tb_id)

    def player_to_dict(p):
        stats = p.get("stats", {})
        kills = stats.get("kills", 0)
        deaths = stats.get("deaths", 0)
        assists = stats.get("assists", 0)
        kda = (kills + assists) / deaths if deaths > 0 else float(kills + assists)
        return {
            "id": p.get("id"),
            "ingame_id": p.get("ingame_id"),
            "name": p.get("name"),
            "role": p.get("role"),
            "kills": kills,
            "deaths": deaths,
            "assists": assists,
            "kda": round(kda, 2),
        }

    if output_format == "json":
        full_data = {
            "match": match_data,
            "team_a": team_a,
            "team_b": team_b,
            "tournament": tour,
            "head_to_head": {
                "total": len(h2h_matches),
                "team_a_wins": h2h_wins_a,
                "team_b_wins": h2h_wins_b,
                "recent": h2h_matches[:5],
            },
            "core_players": {
                "team_a": [player_to_dict(p) for p in team_a_core],
                "team_b": [player_to_dict(p) for p in team_b_core],
            },
            "recent_form": {
                "team_a": {
                    "wins_last_5": team_a_recent_wins,
                    "matches": team_a_form,
                },
                "team_b": {
                    "wins_last_5": team_b_recent_wins,
                    "matches": team_b_form,
                },
            },
        }
        content = json.dumps(full_data, ensure_ascii=False, indent=2)
    elif output_format == "md":
        content = _generate_match_report_md(match_data, team_a, team_b, tour,
                                            h2h_matches, h2h_wins_a, h2h_wins_b,
                                            team_a_core, team_b_core,
                                            team_a_form, team_a_recent_wins,
                                            team_b_form, team_b_recent_wins,
                                            teams, ctx.date_fmt)
    else:
        content = _generate_match_report_text(match_data, team_a, team_b, tour,
                                              h2h_matches, h2h_wins_a, h2h_wins_b,
                                              team_a_core, team_b_core,
                                              team_a_form, team_a_recent_wins,
                                              team_b_form, team_b_recent_wins,
                                              teams, ctx.date_fmt)

    if output:
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
        print_success(f"战报已导出到: {output_path}")
    else:
        print_panel(f"比赛战报 - {match_id}", content)


def _generate_match_report_text(match_data, team_a, team_b, tour,
                                h2h_matches, h2h_wins_a, h2h_wins_b,
                                team_a_core, team_b_core,
                                team_a_form, team_a_recent_wins,
                                team_b_form, team_b_recent_wins,
                                teams_map, date_fmt):
    lines = []
    lines.append("=" * 60)
    lines.append(f"比赛战报: {match_data.get('id', '')}")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"赛事: {tour.get('name', '-')}")
    lines.append(f"阶段: {match_data.get('stage', '-')}")
    lines.append(f"时间: {format_datetime(match_data.get('datetime', '-'), date_fmt)}")
    lines.append(f"赛制: BO{match_data.get('bo', 3)}")
    lines.append(f"状态: {match_data.get('status', '-')}")
    lines.append("")
    lines.append(f"对阵:")
    lines.append(f"  {team_a.get('name', 'TBD')}  vs  {team_b.get('name', 'TBD')}")
    lines.append(f"  总比分: {match_data.get('score_a', 0)} : {match_data.get('score_b', 0)}")
    lines.append("")

    if match_data.get("maps"):
        lines.append("-" * 60)
        lines.append("地图胜负详情:")
        lines.append("-" * 60)
        for i, mp in enumerate(match_data["maps"], 1):
            winner = team_a.get("name", "A") if mp.get("winner", "").upper() == "A" else team_b.get("name", "B")
            lines.append(f"地图 {i}: {mp.get('map_name', '-')}")
            lines.append(f"  比分: {mp.get('score_a', 0)} : {mp.get('score_b', 0)}")
            lines.append(f"  胜者: {winner}")
            if mp.get("duration"):
                lines.append(f"  时长: {mp['duration']}")
            lines.append("")

    if match_data.get("mvp"):
        lines.append(f"MVP: {match_data['mvp']}")
    if match_data.get("duration"):
        lines.append(f"总时长: {match_data['duration']}")
    if match_data.get("notes"):
        lines.append("")
        lines.append(f"备注: {match_data['notes']}")

    lines.append("")
    lines.append("-" * 60)
    lines.append("核心选手 KDA 对比:")
    lines.append("-" * 60)
    lines.append(f"  {team_a.get('name', 'A'):<20} | {team_b.get('name', 'B'):<20}")
    lines.append(f"  {'-' * 20} | {'-' * 20}")
    max_players = max(len(team_a_core), len(team_b_core))
    for i in range(max_players):
        pa = team_a_core[i] if i < len(team_a_core) else None
        pb = team_b_core[i] if i < len(team_b_core) else None
        if pa:
            stats_a = pa.get("stats", {})
            ka = stats_a.get("kills", 0)
            da = stats_a.get("deaths", 0)
            aa = stats_a.get("assists", 0)
            kda_a = (ka + aa) / da if da > 0 else float(ka + aa)
            a_str = f"{pa.get('ingame_id', ''):<8} KDA:{kda_a:.2f}"
        else:
            a_str = " " * 20
        if pb:
            stats_b = pb.get("stats", {})
            kb = stats_b.get("kills", 0)
            db = stats_b.get("deaths", 0)
            ab = stats_b.get("assists", 0)
            kda_b = (kb + ab) / db if db > 0 else float(kb + ab)
            b_str = f"{pb.get('ingame_id', ''):<8} KDA:{kda_b:.2f}"
        else:
            b_str = " " * 20
        lines.append(f"  {a_str:<20} | {b_str:<20}")

    lines.append("")
    lines.append("-" * 60)
    lines.append("近期状态对比 (近5场):")
    lines.append("-" * 60)
    lines.append(f"  {team_a.get('name', 'A')}: {team_a_recent_wins}胜{len(team_a_form) - team_a_recent_wins}负")
    form_a = " ".join(m["result"] for m in team_a_form)
    lines.append(f"  走势: {form_a if form_a else '-'}")
    lines.append("")
    lines.append(f"  {team_b.get('name', 'B')}: {team_b_recent_wins}胜{len(team_b_form) - team_b_recent_wins}负")
    form_b = " ".join(m["result"] for m in team_b_form)
    lines.append(f"  走势: {form_b if form_b else '-'}")

    lines.append("")
    lines.append("-" * 60)
    lines.append("双方历史交手摘要:")
    lines.append("-" * 60)
    lines.append(f"历史交锋: {len(h2h_matches)} 场")
    lines.append(f"  {team_a.get('name', 'A')} 胜: {h2h_wins_a} 场")
    lines.append(f"  {team_b.get('name', 'B')} 胜: {h2h_wins_b} 场")
    lines.append(f"  胜率: {calculate_win_rate(h2h_wins_a, h2h_wins_b)} (对 {team_b.get('name', 'B')})")

    if h2h_matches:
        lines.append("")
        lines.append("近期交手记录:")
        for m in h2h_matches[:5]:
            is_a = m.get("team_a_id") == team_a.get("id")
            my_score = m.get("score_a", 0) if is_a else m.get("score_b", 0)
            opp_score = m.get("score_b", 0) if is_a else m.get("score_a", 0)
            result = "胜" if my_score > opp_score else "负"
            opp_name = team_b.get("name", "") if is_a else team_a.get("name", "")
            lines.append(f"  {format_date(m.get('date', '-'), date_fmt)} - BO{m.get('bo', 3)} {result} "
                         f"({my_score}:{opp_score}) vs {opp_name}")

    lines.append("")
    lines.append("=" * 60)
    return "\n".join(lines)


def _generate_match_report_md(match_data, team_a, team_b, tour,
                              h2h_matches, h2h_wins_a, h2h_wins_b,
                              team_a_core, team_b_core,
                              team_a_form, team_a_recent_wins,
                              team_b_form, team_b_recent_wins,
                              teams_map, date_fmt):
    lines = []
    lines.append(f"# 比赛战报: {match_data.get('id', '')}")
    lines.append("")
    lines.append("## 基本信息")
    lines.append("")
    lines.append(f"- **赛事**: {tour.get('name', '-')}")
    lines.append(f"- **阶段**: {match_data.get('stage', '-')}")
    lines.append(f"- **时间**: {format_datetime(match_data.get('datetime', '-'), date_fmt)}")
    lines.append(f"- **赛制**: BO{match_data.get('bo', 3)}")
    lines.append(f"- **状态**: {match_data.get('status', '-')}")
    lines.append("")
    lines.append("## 对阵情况")
    lines.append("")
    lines.append(f"| 队伍 | 比分 |")
    lines.append(f"|------|------|")
    lines.append(f"| {team_a.get('name', 'TBD')} | {match_data.get('score_a', 0)} |")
    lines.append(f"| {team_b.get('name', 'TBD')} | {match_data.get('score_b', 0)} |")
    lines.append("")

    if match_data.get("maps"):
        lines.append("## 地图胜负详情")
        lines.append("")
        lines.append("| 序号 | 地图 | 队伍A | 队伍B | 胜者 | 时长 |")
        lines.append("|------|------|-------|-------|------|------|")
        for i, mp in enumerate(match_data["maps"], 1):
            winner = team_a.get("name", "A") if mp.get("winner", "").upper() == "A" else team_b.get("name", "B")
            lines.append(f"| {i} | {mp.get('map_name', '-')} | {mp.get('score_a', 0)} | {mp.get('score_b', 0)} | {winner} | {mp.get('duration', '-')} |")
        lines.append("")

    if match_data.get("mvp"):
        lines.append("## MVP")
        lines.append("")
        lines.append(f"{match_data['mvp']}")
        lines.append("")

    if match_data.get("duration"):
        lines.append(f"- **总时长**: {match_data['duration']}")
        lines.append("")

    if match_data.get("notes"):
        lines.append("## 备注")
        lines.append("")
        lines.append(match_data["notes"])
        lines.append("")

    lines.append("## 核心选手 KDA 对比")
    lines.append("")
    lines.append(f"### {team_a.get('name', 'A')}")
    lines.append("")
    lines.append("| 游戏ID | 姓名 | 角色 | 击杀 | 死亡 | 助攻 | KDA |")
    lines.append("|--------|------|------|------|------|------|-----|")
    for p in team_a_core:
        stats_a = p.get("stats", {})
        ka = stats_a.get("kills", 0)
        da = stats_a.get("deaths", 0)
        aa = stats_a.get("assists", 0)
        kda_a = (ka + aa) / da if da > 0 else float(ka + aa)
        lines.append(f"| {p.get('ingame_id', '')} | {p.get('name', '')} | "
                     f"{p.get('role', '')} | {ka} | {da} | {aa} | {kda_a:.2f} |")
    if not team_a_core:
        lines.append("| - | - | - | - | - | - | - |")
    lines.append("")
    lines.append(f"### {team_b.get('name', 'B')}")
    lines.append("")
    lines.append("| 游戏ID | 姓名 | 角色 | 击杀 | 死亡 | 助攻 | KDA |")
    lines.append("|--------|------|------|------|------|------|-----|")
    for p in team_b_core:
        stats_b = p.get("stats", {})
        kb = stats_b.get("kills", 0)
        db = stats_b.get("deaths", 0)
        ab = stats_b.get("assists", 0)
        kda_b = (kb + ab) / db if db > 0 else float(kb + ab)
        lines.append(f"| {p.get('ingame_id', '')} | {p.get('name', '')} | "
                     f"{p.get('role', '')} | {kb} | {db} | {ab} | {kda_b:.2f} |")
    if not team_b_core:
        lines.append("| - | - | - | - | - | - | - |")
    lines.append("")

    lines.append("## 近期状态对比 (近5场)")
    lines.append("")
    lines.append(f"### {team_a.get('name', 'A')}")
    lines.append("")
    lines.append(f"- **战绩**: {team_a_recent_wins}胜{len(team_a_form) - team_a_recent_wins}负")
    form_a = " ".join(m["result"] for m in team_a_form)
    lines.append(f"- **走势**: {form_a if form_a else '-'}")
    lines.append("")
    if team_a_form:
        lines.append("| 日期 | 对手 | 结果 | 比分 |")
        lines.append("|------|------|------|------|")
        for m in team_a_form:
            opp_name = teams_map.get(m.get("opponent", ""), {}).get("name", m.get("opponent", ""))
            lines.append(f"| {format_date(m.get('date', '-'), date_fmt)} | {opp_name} | {m['result']} | {m['score']} |")
        lines.append("")

    lines.append(f"### {team_b.get('name', 'B')}")
    lines.append("")
    lines.append(f"- **战绩**: {team_b_recent_wins}胜{len(team_b_form) - team_b_recent_wins}负")
    form_b = " ".join(m["result"] for m in team_b_form)
    lines.append(f"- **走势**: {form_b if form_b else '-'}")
    lines.append("")
    if team_b_form:
        lines.append("| 日期 | 对手 | 结果 | 比分 |")
        lines.append("|------|------|------|------|")
        for m in team_b_form:
            opp_name = teams_map.get(m.get("opponent", ""), {}).get("name", m.get("opponent", ""))
            lines.append(f"| {format_date(m.get('date', '-'), date_fmt)} | {opp_name} | {m['result']} | {m['score']} |")
        lines.append("")

    lines.append("## 历史交手摘要")
    lines.append("")
    lines.append(f"- **历史交锋**: {len(h2h_matches)} 场")
    lines.append(f"- **{team_a.get('name', 'A')} 胜**: {h2h_wins_a} 场")
    lines.append(f"- **{team_b.get('name', 'B')} 胜**: {h2h_wins_b} 场")
    lines.append(f"- **{team_a.get('name', 'A')} 胜率**: {calculate_win_rate(h2h_wins_a, h2h_wins_b)}")
    lines.append("")

    if h2h_matches:
        lines.append("### 近期交手记录")
        lines.append("")
        lines.append("| 日期 | 赛事 | 赛制 | 结果 | 比分 |")
        lines.append("|------|------|------|------|------|")
        for m in h2h_matches[:5]:
            is_a = m.get("team_a_id") == team_a.get("id")
            my_score = m.get("score_a", 0) if is_a else m.get("score_b", 0)
            opp_score = m.get("score_b", 0) if is_a else m.get("score_a", 0)
            result = "胜" if my_score > opp_score else "负"
            lines.append(f"| {format_date(m.get('date', '-'), date_fmt)} | {m.get('stage', '-')} | BO{m.get('bo', 3)} | {result} | {my_score}:{opp_score} |")
        lines.append("")

    return "\n".join(lines)


@report_cmd.command("team")
@click.argument("team_id")
@click.option("--tournament", "-t", help="赛事ID")
@click.option("--date-from", help="开始日期 (YYYY-MM-DD)")
@click.option("--date-to", help="结束日期 (YYYY-MM-DD)")
@click.option("--available-only", is_flag=True, help="只统计可出场选手")
@click.option("--min-players", type=int, default=5, help="最低出场人数要求")
@click.option("--format", "-f", "output_format", default="text",
              type=click.Choice(["text", "md", "json"]),
              help="输出格式")
@click.option("--output", "-o", default="", help="输出文件路径")
@pass_context
def report_team(ctx, team_id, tournament, date_from, date_to,
                available_only, min_players, output_format, output):
    """生成队伍战绩报告"""
    teams = ctx.db.load_teams()
    matches = ctx.db.load_matches()
    players = ctx.db.load_players()
    teams_map = {t["id"]: t for t in teams}
    tournaments = {t["id"]: t for t in ctx.db.load_tournaments()}

    team_data = next((t for t in teams if t.get("id") == team_id), None)
    if not team_data:
        print_error(f"未找到队伍: {team_id}")
        return

    from datetime import datetime
    if date_from:
        try:
            date_from_dt = datetime.strptime(date_from, "%Y-%m-%d")
        except ValueError:
            print_error("日期格式错误，请使用 YYYY-MM-DD")
            return
    if date_to:
        try:
            date_to_dt = datetime.strptime(date_to, "%Y-%m-%d")
            date_to_dt = date_to_dt.replace(hour=23, minute=59, second=59)
        except ValueError:
            print_error("日期格式错误，请使用 YYYY-MM-DD")
            return

    team_matches = []
    for m in matches:
        if m.get("status") != "finished":
            continue
        if tournament and m.get("tournament_id") != tournament:
            continue
        if m.get("team_a_id") != team_id and m.get("team_b_id") != team_id:
            continue

        if date_from or date_to:
            match_date_str = m.get("date", "")
            if match_date_str:
                try:
                    match_date = datetime.strptime(match_date_str, "%Y-%m-%d")
                    if date_from and match_date < date_from_dt:
                        continue
                    if date_to and match_date > date_to_dt:
                        continue
                except ValueError:
                    pass

        team_matches.append(m)

    team_matches.sort(key=lambda x: x.get("datetime", ""), reverse=True)

    wins = 0
    losses = 0
    score_for = 0
    score_against = 0
    map_wins = 0
    map_losses = 0
    opponent_stats = {}
    tournament_stats = {}
    recent_form = []

    for m in team_matches:
        is_a = m.get("team_a_id") == team_id
        s_a = m.get("score_a", 0)
        s_b = m.get("score_b", 0)
        opp_id = m.get("team_b_id") if is_a else m.get("team_a_id")
        opp_name = teams_map.get(opp_id, {}).get("name", opp_id)
        tour_id = m.get("tournament_id", "")
        tour_name = tournaments.get(tour_id, {}).get("name", tour_id)

        maps = m.get("maps", [])
        for mp in maps:
            ms_a = mp.get("score_a", 0)
            ms_b = mp.get("score_b", 0)
            if is_a:
                map_wins += ms_a
                map_losses += ms_b
            else:
                map_wins += ms_b
                map_losses += ms_a

        if is_a:
            score_for += s_a
            score_against += s_b
            if s_a > s_b:
                wins += 1
                result = "胜"
            elif s_a < s_b:
                losses += 1
                result = "负"
            else:
                result = "平"
        else:
            score_for += s_b
            score_against += s_a
            if s_b > s_a:
                wins += 1
                result = "胜"
            elif s_b < s_a:
                losses += 1
                result = "负"
            else:
                result = "平"

        if opp_id not in opponent_stats:
            opponent_stats[opp_id] = {"name": opp_name, "wins": 0, "losses": 0}
        if result == "胜":
            opponent_stats[opp_id]["wins"] += 1
        elif result == "负":
            opponent_stats[opp_id]["losses"] += 1

        if tour_id not in tournament_stats:
            tournament_stats[tour_id] = {"name": tour_name, "wins": 0, "losses": 0}
        if result == "胜":
            tournament_stats[tour_id]["wins"] += 1
        elif result == "负":
            tournament_stats[tour_id]["losses"] += 1

        recent_form.append({
            "date": m.get("date", ""),
            "opponent": opp_name,
            "tournament": tour_name,
            "result": result,
            "score": f"{s_a if is_a else s_b}:{s_b if is_a else s_a}",
            "bo": m.get("bo", 3),
        })

    total = wins + losses
    win_rate = (wins / total * 100) if total > 0 else 0
    map_diff = map_wins - map_losses

    team_players = [p for p in players if p.get("team_id") == team_id]

    status_counts = {}
    for p in team_players:
        s = normalize_player_status(p.get("status", "active"))
        status_counts[s] = status_counts.get(s, 0) + 1

    available_count = sum(1 for p in team_players if is_player_available(p.get("status", "active")))
    meets_min = available_count >= min_players

    display_players = [p for p in team_players if is_player_available(p.get("status", "active"))] if available_only else team_players

    player_stats = []
    for p in display_players:
        stats = p.get("stats", {})
        kills = stats.get("kills", 0)
        deaths = stats.get("deaths", 0)
        assists = stats.get("assists", 0)
        kda = (kills + assists) / deaths if deaths > 0 else float(kills + assists)
        player_stats.append({
            "id": p.get("id"),
            "ingame_id": p.get("ingame_id", ""),
            "name": p.get("name", ""),
            "role": p.get("role", ""),
            "status": normalize_player_status(p.get("status", "active")),
            "kills": kills,
            "deaths": deaths,
            "assists": assists,
            "kda": round(kda, 2),
        })
    player_stats.sort(key=lambda x: -x["kda"])

    roster_info = {
        "total": len(team_players),
        "active": status_counts.get("active", 0),
        "substitute": status_counts.get("substitute", 0),
        "suspended": status_counts.get("suspended", 0),
        "injured": status_counts.get("injured", 0),
        "available": available_count,
        "min_required": min_players,
        "meets_minimum": meets_min,
        "available_only": available_only,
    }

    date_range_info = {
        "from": date_from,
        "to": date_to,
    }

    if output_format == "json":
        full_data = {
            "team": team_data,
            "date_range": date_range_info,
            "roster": roster_info,
            "summary": {
                "total_matches": total,
                "wins": wins,
                "losses": losses,
                "win_rate": f"{win_rate:.2f}%",
                "score_for": score_for,
                "score_against": score_against,
                "score_diff": score_for - score_against,
                "map_wins": map_wins,
                "map_losses": map_losses,
                "map_diff": map_diff,
            },
            "recent_form": recent_form[:10],
            "opponent_stats": list(opponent_stats.values()),
            "tournament_stats": list(tournament_stats.values()),
            "players": player_stats,
        }
        content = json.dumps(full_data, ensure_ascii=False, indent=2)
    elif output_format == "md":
        content = _generate_team_report_md(team_data, total, wins, losses, win_rate,
                                           score_for, score_against, recent_form,
                                           opponent_stats, tournament_stats,
                                           player_stats, map_wins, map_losses, map_diff,
                                           date_range_info, roster_info, ctx.date_fmt)
    else:
        content = _generate_team_report_text(team_data, total, wins, losses, win_rate,
                                             score_for, score_against, recent_form,
                                             opponent_stats, tournament_stats,
                                             player_stats, map_wins, map_losses, map_diff,
                                             date_range_info, roster_info, ctx.date_fmt)

    if output:
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
        print_success(f"队伍报告已导出到: {output_path}")
    else:
        print_panel(f"队伍报告 - {team_data.get('name', '')}", content)


def _generate_team_report_text(team_data, total, wins, losses, win_rate,
                               score_for, score_against, recent_form,
                               opponent_stats, tournament_stats,
                               player_stats, map_wins, map_losses, map_diff,
                               date_range_info, roster_info, date_fmt):
    lines = []
    lines.append("=" * 70)
    lines.append(f"队伍战绩报告: {team_data.get('name', '')}")
    lines.append("=" * 70)
    lines.append("")
    if date_range_info.get("from") or date_range_info.get("to"):
        df = date_range_info.get("from", "最早")
        dt = date_range_info.get("to", "最新")
        lines.append(f"统计区间: {df} ~ {dt}")
        lines.append("")
    lines.append(f"总场次: {total}  胜场: {wins}  败场: {losses}  胜率: {win_rate:.2f}%")
    lines.append(f"总得分: {score_for}  总失分: {score_against}  净胜分: {score_for - score_against:+d}")
    lines.append(f"地图胜: {map_wins}  地图负: {map_losses}  净胜图: {map_diff:+d}")
    lines.append("")

    if roster_info:
        r = roster_info
        meets = "✓ 满足" if r["meets_minimum"] else "✗ 不满足"
        lines.append(f"阵容统计: 总计{r['total']}人 | "
                     f"正常{r['active']} | 替补{r['substitute']} | "
                     f"禁赛{r['suspended']} | 受伤{r['injured']}")
        lines.append(f"可出场: {r['available']} 人 (最低要求 {r['min_required']} 人) -> {meets}")
        if r.get("available_only"):
            lines.append("  (仅显示可出场选手)")
        lines.append("")

    lines.append("-" * 70)
    lines.append("最近战绩走势 (近10场):")
    lines.append("-" * 70)
    form_str = "  ".join(m["result"] for m in recent_form[:10])
    lines.append(f"  {form_str}" if form_str else "  暂无数据")
    lines.append("")

    lines.append("-" * 70)
    lines.append("近期比赛详情:")
    lines.append("-" * 70)
    lines.append(f"  {'日期':<12} {'赛事':<10} {'对手':<10} {'赛制':<6} {'结果':<4} 比分")
    lines.append(f"  {'-'*12} {'-'*10} {'-'*10} {'-'*6} {'-'*4} {'-'*6}")
    for m in recent_form[:10]:
        lines.append(f"  {format_date(m['date'], date_fmt):<12} {m['tournament']:<10} {m['opponent']:<10} "
                     f"BO{m['bo']:<4} {m['result']:<4} {m['score']}")
    lines.append("")

    if player_stats:
        lines.append("-" * 70)
        lines.append("选手数据 (按KDA排序):")
        lines.append("-" * 70)
        lines.append(f"  {'游戏ID':<10} {'角色':<6} {'击杀':<6} {'死亡':<6} {'助攻':<6} {'KDA':<8} {'状态':<8}")
        lines.append(f"  {'-'*10} {'-'*6} {'-'*6} {'-'*6} {'-'*6} {'-'*8} {'-'*8}")
        for p in player_stats[:8]:
            status = get_player_status_label(p["status"])
            lines.append(f"  {p['ingame_id']:<10} {p['role']:<6} {p['kills']:<6} "
                         f"{p['deaths']:<6} {p['assists']:<6} {p['kda']:<8} {status:<8}")
        if len(player_stats) > 8:
            lines.append(f"  ... 还有 {len(player_stats) - 8} 名选手")
        lines.append("")

    if tournament_stats:
        lines.append("-" * 70)
        lines.append("各赛事战绩:")
        lines.append("-" * 70)
        lines.append(f"  {'赛事名称':<16} {'场次':<6} {'胜':<4} {'负':<4} {'胜率':<8}")
        lines.append(f"  {'-'*16} {'-'*6} {'-'*4} {'-'*4} {'-'*8}")
        for tid, ts in tournament_stats.items():
            t = ts["wins"] + ts["losses"]
            wr = f"{ts['wins']/t*100:.1f}%" if t > 0 else "-"
            lines.append(f"  {ts['name']:<16} {t:<6} {ts['wins']:<4} {ts['losses']:<4} {wr:<8}")
        lines.append("")

    if opponent_stats:
        lines.append("-" * 70)
        lines.append("对手交锋记录:")
        lines.append("-" * 70)
        lines.append(f"  {'对手':<12} {'场次':<6} {'胜':<4} {'负':<4} {'胜率':<8}")
        lines.append(f"  {'-'*12} {'-'*6} {'-'*4} {'-'*4} {'-'*8}")
        sorted_opp = sorted(opponent_stats.items(),
                            key=lambda x: x[1]["wins"] + x[1]["losses"], reverse=True)
        for oid, os_ in sorted_opp[:8]:
            t = os_["wins"] + os_["losses"]
            wr = f"{os_['wins']/t*100:.1f}%" if t > 0 else "-"
            lines.append(f"  {os_['name']:<12} {t:<6} {os_['wins']:<4} {os_['losses']:<4} {wr:<8}")
        lines.append("")

    lines.append("=" * 70)
    return "\n".join(lines)


def _generate_team_report_md(team_data, total, wins, losses, win_rate,
                             score_for, score_against, recent_form,
                             opponent_stats, tournament_stats,
                             player_stats, map_wins, map_losses, map_diff,
                             date_range_info, roster_info, date_fmt):
    lines = []
    lines.append(f"# 队伍战绩报告: {team_data.get('name', '')}")
    lines.append("")
    if date_range_info.get("from") or date_range_info.get("to"):
        df = date_range_info.get("from", "最早")
        dt = date_range_info.get("to", "最新")
        lines.append(f"**统计区间**: {df} ~ {dt}")
        lines.append("")
    lines.append("## 战绩概览")
    lines.append("")
    lines.append("| 指标 | 数值 |")
    lines.append("|------|------|")
    lines.append(f"| 总场次 | {total} |")
    lines.append(f"| 胜场 | {wins} |")
    lines.append(f"| 败场 | {losses} |")
    lines.append(f"| 胜率 | {win_rate:.2f}% |")
    lines.append(f"| 总得分 | {score_for} |")
    lines.append(f"| 总失分 | {score_against} |")
    lines.append(f"| 净胜分 | {score_for - score_against:+d} |")
    lines.append(f"| 地图胜 | {map_wins} |")
    lines.append(f"| 地图负 | {map_losses} |")
    lines.append(f"| 净胜图 | {map_diff:+d} |")
    lines.append("")

    if roster_info:
        r = roster_info
        meets = "是" if r["meets_minimum"] else "否"
        lines.append("## 阵容统计")
        lines.append("")
        lines.append("| 指标 | 数值 |")
        lines.append("|------|------|")
        lines.append(f"| 总人数 | {r['total']} |")
        lines.append(f"| 正常 | {r['active']} |")
        lines.append(f"| 替补 | {r['substitute']} |")
        lines.append(f"| 禁赛 | {r['suspended']} |")
        lines.append(f"| 受伤 | {r['injured']} |")
        lines.append(f"| 可出场 | {r['available']} |")
        lines.append(f"| 最低要求 | {r['min_required']} 人 |")
        lines.append(f"| 是否满足最低要求 | {meets} |")
        lines.append("")

    lines.append("## 最近战绩走势 (近10场)")
    lines.append("")
    form_str = " ".join(m["result"] for m in recent_form[:10])
    lines.append(form_str if form_str else "暂无数据")
    lines.append("")

    lines.append("## 近期比赛详情")
    lines.append("")
    lines.append("| 日期 | 赛事 | 对手 | 赛制 | 结果 | 比分 |")
    lines.append("|------|------|------|------|------|------|")
    for m in recent_form[:10]:
        lines.append(f"| {format_date(m['date'], date_fmt)} | {m['tournament']} | {m['opponent']} | "
                     f"BO{m['bo']} | {m['result']} | {m['score']} |")
    lines.append("")

    if player_stats:
        lines.append("## 选手数据 (按KDA排序)")
        lines.append("")
        lines.append("| 游戏ID | 姓名 | 角色 | 击杀 | 死亡 | 助攻 | KDA | 状态 |")
        lines.append("|--------|------|------|------|------|------|-----|------|")
        for p in player_stats:
            status = get_player_status_label(p["status"])
            lines.append(f"| {p['ingame_id']} | {p['name']} | {p['role']} | "
                         f"{p['kills']} | {p['deaths']} | {p['assists']} | {p['kda']} | {status} |")
        lines.append("")

    if tournament_stats:
        lines.append("## 各赛事战绩")
        lines.append("")
        lines.append("| 赛事名称 | 场次 | 胜 | 负 | 胜率 |")
        lines.append("|----------|------|----|----|------|")
        for tid, ts in tournament_stats.items():
            t = ts["wins"] + ts["losses"]
            wr = f"{ts['wins']/t*100:.1f}%" if t > 0 else "-"
            lines.append(f"| {ts['name']} | {t} | {ts['wins']} | {ts['losses']} | {wr} |")
        lines.append("")

    if opponent_stats:
        lines.append("## 对手交锋记录")
        lines.append("")
        lines.append("| 对手 | 场次 | 胜 | 负 | 胜率 |")
        lines.append("|------|------|----|----|------|")
        sorted_opp = sorted(opponent_stats.items(),
                            key=lambda x: x[1]["wins"] + x[1]["losses"], reverse=True)
        for oid, os_ in sorted_opp[:8]:
            t = os_["wins"] + os_["losses"]
            wr = f"{os_['wins']/t*100:.1f}%" if t > 0 else "-"
            lines.append(f"| {os_['name']} | {t} | {os_['wins']} | {os_['losses']} | {wr} |")
        lines.append("")

    return "\n".join(lines)


@report_cmd.command("filter")
@click.option("--tournament", "-t", help="赛事ID")
@click.option("--team", "-T", help="队伍ID")
@click.option("--date-from", help="开始日期")
@click.option("--date-to", help="结束日期")
@click.option("--status", "-s", help="比赛状态")
@click.option("--min-score", type=int, help="最低总比分")
@click.option("--has-mvp", is_flag=True, help="有MVP的比赛")
@pass_context
def report_filter(ctx, tournament, team, date_from, date_to, status, min_score, has_mvp):
    """关键数据筛选"""
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

    if date_from:
        filtered = [m for m in filtered if m.get("date", "") >= date_from]

    if date_to:
        filtered = [m for m in filtered if m.get("date", "") <= date_to]

    if status:
        filtered = [m for m in filtered if m.get("status") == status]

    if min_score is not None:
        filtered = [
            m for m in filtered
            if (m.get("score_a", 0) + m.get("score_b", 0)) >= min_score
        ]

    if has_mvp:
        filtered = [m for m in filtered if m.get("mvp")]

    filtered.sort(key=lambda x: x.get("datetime", ""), reverse=True)

    if not filtered:
        print_info("没有符合条件的比赛")
        return

    rows = []
    for m in filtered:
        team_a = teams.get(m.get("team_a_id", ""), {}).get("name", "TBD")
        team_b = teams.get(m.get("team_b_id", ""), {}).get("name", "TBD")
        tour_name = tournaments.get(m.get("tournament_id", ""), {}).get("name", "-")
        score = f"{m.get('score_a', 0)}:{m.get('score_b', 0)}"

        rows.append([
            m.get("id", "-"),
            format_date(m.get("date", "-"), ctx.date_fmt),
            tour_name,
            m.get("stage", "-"),
            f"{team_a} vs {team_b}",
            score,
            m.get("mvp", "-"),
        ])

    print_table(
        "数据筛选结果",
        ["比赛ID", "日期", "赛事", "阶段", "对阵", "比分", "MVP"],
        rows,
        table_style=ctx.table_style,
    )
    print_info(f"共找到 {len(filtered)} 场符合条件的比赛")


@report_cmd.command("export")
@click.argument("data_type", type=click.Choice(["matches", "teams", "players", "schedules", "all"]))
@click.option("--format", "-f", "output_format", default="json",
              type=click.Choice(["json", "csv"]),
              help="导出格式")
@click.option("--output", "-o", default="", help="输出目录")
@pass_context
def report_export(ctx, data_type, output_format, output):
    """批量导出数据"""
    if not output:
        output = os.path.join(os.getcwd(), "esports_export")

    output_dir = Path(output)
    output_dir.mkdir(parents=True, exist_ok=True)

    exported_files = []

    data_sources = {
        "matches": (ctx.db.load_matches, "matches"),
        "teams": (ctx.db.load_teams, "teams"),
        "players": (ctx.db.load_players, "players"),
        "schedules": (ctx.db.load_schedules, "schedules"),
    }

    if data_type == "all":
        targets = list(data_sources.keys())
    else:
        targets = [data_type]

    for target in targets:
        load_func, filename = data_sources[target]
        data = load_func()

        if output_format == "json":
            import json
            filepath = output_dir / f"{filename}.json"
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            exported_files.append(str(filepath))
        else:
            filepath = output_dir / f"{filename}.csv"
            if data and isinstance(data, list):
                import csv
                keys = set()
                for item in data:
                    if isinstance(item, dict):
                        keys.update(item.keys())
                keys = sorted(keys)
                with open(filepath, "w", encoding="utf-8-sig", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=keys)
                    writer.writeheader()
                    for item in data:
                        if isinstance(item, dict):
                            writer.writerow(item)
                exported_files.append(str(filepath))

    print_success(f"数据导出完成，共 {len(exported_files)} 个文件:")
    for f in exported_files:
        print_info(f"  - {f}")


def _validate_import_data(ctx, data_type, data, extra_team_ids=None, extra_tournament_ids=None):
    """统一的导入数据校验函数，返回 (valid_items, results)

    results 结构:
        total, success, failed, skipped,
        error_types: {duplicate_id, missing_fields, invalid_date, missing_ref, ...},
        errors: [详细错误列表]

    extra_team_ids / extra_tournament_ids: 额外视为有效的引用 ID（用于同一导入包内的依赖预检）
    """
    required_fields_map = {
        "teams": ["id", "name", "region"],
        "players": ["id", "name", "team_id", "role"],
        "matches": ["id", "tournament_id", "team_a_id", "team_b_id", "datetime"],
        "schedules": ["id", "tournament_id", "team_a_id", "team_b_id", "datetime"],
    }
    required_fields = required_fields_map.get(data_type, [])

    load_map = {
        "teams": ctx.db.load_teams,
        "players": ctx.db.load_players,
        "matches": ctx.db.load_matches,
        "schedules": ctx.db.load_schedules,
    }
    existing_data = load_map[data_type]()
    existing_ids = {item.get("id") for item in existing_data}

    teams_ids = {t["id"] for t in ctx.db.load_teams()}
    tournament_ids = {t["id"] for t in ctx.db.load_tournaments()}
    if extra_team_ids:
        teams_ids = teams_ids | set(extra_team_ids)
    if extra_tournament_ids:
        tournament_ids = tournament_ids | set(extra_tournament_ids)

    results = {
        "total": len(data),
        "success": 0,
        "failed": 0,
        "skipped": 0,
        "error_types": {
            "duplicate_existing": 0,
            "duplicate_in_file": 0,
            "missing_fields": 0,
            "invalid_date": 0,
            "missing_ref_team": 0,
            "missing_ref_tournament": 0,
        },
        "errors": [],
    }

    seen_ids = set()
    id_indices = {}
    valid_items = []
    duplicate_ids = set()

    for idx, item in enumerate(data, 1):
        item_id = item.get("id", "")
        if item_id:
            if item_id not in id_indices:
                id_indices[item_id] = []
            id_indices[item_id].append(idx)

    for item_id, indices in id_indices.items():
        if item_id not in existing_ids and len(indices) > 1:
            duplicate_ids.add(item_id)

    for idx, item in enumerate(data, 1):
        item_id = item.get("id", "")

        if not item_id:
            results["failed"] += 1
            results["error_types"]["missing_fields"] += 1
            results["errors"].append(f"第 {idx} 条: 缺少 id 字段")
            continue

        if item_id in existing_ids:
            results["skipped"] += 1
            results["error_types"]["duplicate_existing"] += 1
            results["errors"].append(f"第 {idx} 条 (ID: {item_id}): 已存在，跳过")
            continue

        if item_id in duplicate_ids:
            results["failed"] += 1
            results["error_types"]["duplicate_in_file"] += 1
            dup_lines = ", ".join(f"第 {i} 条" for i in id_indices[item_id])
            results["errors"].append(f"第 {idx} 条 (ID: {item_id}): 文件内重复 ID "
                                    f"({dup_lines} 重复)，全部拒绝导入")
            continue

        missing = [f for f in required_fields if not item.get(f)]
        if missing:
            results["failed"] += 1
            results["error_types"]["missing_fields"] += 1
            results["errors"].append(f"第 {idx} 条 (ID: {item_id}): 缺少字段: {', '.join(missing)}")
            continue

        if data_type in ["players"] and item.get("team_id"):
            if item["team_id"] not in teams_ids:
                results["failed"] += 1
                results["error_types"]["missing_ref_team"] += 1
                results["errors"].append(f"第 {idx} 条 (ID: {item_id}): 队伍不存在: {item['team_id']}")
                continue

        if data_type in ["matches", "schedules"]:
            if item.get("tournament_id") and item["tournament_id"] not in tournament_ids:
                results["failed"] += 1
                results["error_types"]["missing_ref_tournament"] += 1
                results["errors"].append(f"第 {idx} 条 (ID: {item_id}): 赛事不存在: {item['tournament_id']}")
                continue
            if item.get("team_a_id") and item["team_a_id"] not in teams_ids:
                results["failed"] += 1
                results["error_types"]["missing_ref_team"] += 1
                results["errors"].append(f"第 {idx} 条 (ID: {item_id}): 队伍A不存在: {item['team_a_id']}")
                continue
            if item.get("team_b_id") and item["team_b_id"] not in teams_ids:
                results["failed"] += 1
                results["error_types"]["missing_ref_team"] += 1
                results["errors"].append(f"第 {idx} 条 (ID: {item_id}): 队伍B不存在: {item['team_b_id']}")
                continue

            if item.get("datetime"):
                valid, _, _ = validate_datetime(item["datetime"])
                if not valid:
                    results["failed"] += 1
                    results["error_types"]["invalid_date"] += 1
                    results["errors"].append(f"第 {idx} 条 (ID: {item_id}): 日期格式无效: {item['datetime']}")
                    continue

        new_item = dict(item)
        if data_type in ["matches", "schedules"]:
            if "datetime" in new_item and "date" not in new_item:
                valid, norm_dt, date_part = validate_datetime(new_item["datetime"])
                if valid:
                    new_item["datetime"] = norm_dt
                    new_item["date"] = date_part

        valid_items.append(new_item)
        results["success"] += 1

    return valid_items, results


def _print_import_results(title, results, table_style):
    """打印导入/预检结果表格"""
    et = results["error_types"]
    detail_rows = [
        ["总记录数", str(results["total"])],
        ["可导入(成功)", str(results["success"])],
        ["失败", str(results["failed"])],
        ["  · 文件内重复ID", str(et["duplicate_in_file"])],
        ["  · 缺失字段", str(et["missing_fields"])],
        ["  · 无效日期", str(et["invalid_date"])],
        ["  · 找不到队伍", str(et["missing_ref_team"])],
        ["  · 找不到赛事", str(et["missing_ref_tournament"])],
        ["跳过(已存在)", str(results["skipped"])],
        ["  · 系统中已存在", str(et["duplicate_existing"])],
    ]

    print_table(title, ["类别", "数量"], detail_rows, table_style=table_style)

    if results["errors"]:
        print_info("")
        print_info("详细信息:")
        for err in results["errors"][:25]:
            print_info(f"  {err}")
        if len(results["errors"]) > 25:
            print_info(f"  ... 还有 {len(results['errors']) - 25} 条提示")


def _import_all(ctx, file_path, input_format, dry_run, summary_json, type_names):
    """事务式导入全部类型，失败回滚"""
    all_data = _read_import_file(file_path, input_format)
    if all_data is None:
        return
    if not isinstance(all_data, dict):
        print_error("all 模式下 JSON 必须是对象，包含 teams/players/matches/schedules 键")
        return

    order = ["teams", "players", "matches", "schedules"]

    print_info("第一步：全部类型预检（含包内依赖识别）...")
    all_valid = {}
    all_results = {}
    extra_team_ids = []
    extra_tournament_ids = []

    precheck_ok = True
    for dt in order:
        items = all_data.get(dt, [])
        if not items:
            continue
        valid_items, results = _validate_import_data(
            ctx, dt, items,
            extra_team_ids=extra_team_ids,
            extra_tournament_ids=extra_tournament_ids,
        )
        all_valid[dt] = valid_items
        all_results[dt] = results
        if results["failed"] > 0:
            precheck_ok = False
        if dt == "teams":
            extra_team_ids = [t["id"] for t in valid_items]

    summary_rows = []
    total_success = 0
    total_failed = 0
    total_skipped = 0
    for dt in order:
        if dt in all_results:
            r = all_results[dt]
            summary_rows.append([type_names[dt], str(r["total"]), str(r["success"]), str(r["failed"]), str(r["skipped"])])
            total_success += r["success"]
            total_failed += r["failed"]
            total_skipped += r["skipped"]

    print_table(
        "导入预检汇总 - 全部类型",
        ["数据类型", "总数", "可导入", "失败", "跳过"],
        summary_rows + [
            ["合计", str(sum(r["total"] for r in all_results.values())),
             str(total_success), str(total_failed), str(total_skipped)]
        ],
        table_style=ctx.table_style,
    )

    if not precheck_ok:
        print_error("")
        print_error(f"预检未通过，共 {total_failed} 条错误。事务已取消，未写入任何数据。")
        for dt in order:
            if dt in all_results and all_results[dt]["errors"]:
                print_info("")
                print_info(f"  {type_names[dt]} 错误详情:")
                for err in all_results[dt]["errors"][:10]:
                    print_info(f"    - {err}")
        return

    print_success("")
    print_success("预检全部通过！")

    if dry_run:
        print_info("试运行模式，未实际保存数据。去掉 --dry-run 参数以实际导入。")
        return

    print_info("")
    print_info("第二步：执行事务式导入...")

    save_map = {
        "teams": (ctx.db.load_teams, ctx.db.save_teams),
        "players": (ctx.db.load_players, ctx.db.save_players),
        "matches": (ctx.db.load_matches, ctx.db.save_matches),
        "schedules": (ctx.db.load_schedules, ctx.db.save_schedules),
    }

    backups = {}
    committed = []
    rollback_count = 0
    failed_type = None
    failed_reason = None

    try:
        for dt in order:
            if dt not in all_valid or not all_valid[dt]:
                continue

            load_func, save_func = save_map[dt]
            original = load_func()
            backups[dt] = original

            combined = original + all_valid[dt]
            save_func(combined)
            committed.append(dt)
            print_info(f"  ✓ 已导入 {type_names[dt]}: {len(all_valid[dt])} 条")

            if dt == "matches":
                schedules = ctx.db.load_schedules()
                sched_ids = {s["id"] for s in schedules}
                sched_backup = backups.get("schedules", schedules[:])
                if "schedules" not in backups:
                    backups["schedules"] = sched_backup
                new_sched = []
                for item in all_valid[dt]:
                    if item["id"] not in sched_ids:
                        sched_item = {k: v for k, v in item.items()
                                      if k not in ["mvp", "duration", "notes", "type"]}
                        sched_item.setdefault("status", "scheduled")
                        sched_item.setdefault("score_a", 0)
                        sched_item.setdefault("score_b", 0)
                        sched_item.setdefault("maps", [])
                        schedules.append(sched_item)
                        new_sched.append(sched_item)
                ctx.db.save_schedules(schedules)
                if new_sched:
                    if "schedules" not in committed:
                        committed.append("schedules")

            if dt == "schedules":
                matches = ctx.db.load_matches()
                match_ids = {m["id"] for m in matches}
                match_backup = backups.get("matches", matches[:])
                if "matches" not in backups:
                    backups["matches"] = match_backup
                new_matches = []
                for item in all_valid[dt]:
                    if item["id"] not in match_ids:
                        match_item = dict(item)
                        match_item.setdefault("mvp", "")
                        match_item.setdefault("duration", "")
                        match_item.setdefault("notes", "")
                        match_item.setdefault("type", "official")
                        matches.append(match_item)
                        new_matches.append(match_item)
                ctx.db.save_matches(matches)
                if new_matches:
                    if "matches" not in committed:
                        committed.append("matches")

    except Exception as e:
        failed_type = dt
        failed_reason = str(e)

    if failed_type:
        print_error("")
        print_error(f"导入 {type_names.get(failed_type, failed_type)} 时出错，开始回滚...")
        print_error(f"失败原因: {failed_reason}")

        for dt in reversed(committed):
            load_func, save_func = save_map[dt]
            if dt in backups:
                save_func(backups[dt])
                rollback_count += len(all_valid.get(dt, []))
                print_info(f"  ↺ 已回滚 {type_names[dt]}")

        print_warning("")
        print_warning(f"事务已回滚，共回滚 {rollback_count} 条数据。")
        print_warning(f"失败类型: {type_names.get(failed_type, failed_type)}")
        print_warning(f"失败原因: {failed_reason}")
        return

    all_new_ids = []
    all_new_items = {}
    for dt in committed:
        all_new_ids.extend([item.get("id") for item in all_valid.get(dt, [])])
        all_new_items[dt] = all_valid.get(dt, [])

    settings = ctx.db.load_settings()
    detail = f"事务式导入 {len(committed)} 类，共 {len(all_new_ids)} 条数据，来自 {file_path}"
    log_operation(ctx.db, settings, "import", "all", all_new_ids, detail,
                  after_data=all_new_items)

    print_success("")
    print_success(f"事务式导入完成！成功导入 {len(all_new_ids)} 条数据，"
                  f"涉及 {len(committed)} 种类型。")


@report_cmd.command("import")
@click.argument("data_type", type=click.Choice(["matches", "teams", "players", "schedules", "all"]))
@click.argument("file_path", type=click.Path(exists=True))
@click.option("--format", "-f", "input_format", default="json",
              type=click.Choice(["json", "csv"]),
              help="输入文件格式")
@click.option("--dry-run", is_flag=True, help="试运行，不实际保存")
@click.option("--summary-json", is_flag=True, help="输出JSON格式的变更摘要")
@pass_context
def report_import(ctx, data_type, file_path, input_format, dry_run, summary_json):
    """批量导入数据（all 模式为事务式导入，失败自动回滚）"""
    type_names = {
        "teams": "队伍",
        "players": "选手",
        "matches": "比赛",
        "schedules": "赛程",
    }

    if data_type == "all":
        _import_all(ctx, file_path, input_format, dry_run, summary_json, type_names)
        return

    data = _read_import_file(file_path, input_format)
    if data is None:
        return

    if not data:
        print_info("文件中没有数据")
        return

    valid_items, results = _validate_import_data(ctx, data_type, data)

    type_names = {
        "teams": "队伍",
        "players": "选手",
        "matches": "比赛",
        "schedules": "赛程",
    }
    title = f"导入结果 - {type_names.get(data_type, data_type)}"
    if dry_run:
        title += " (试运行)"

    _print_import_results(title, results, ctx.table_style)

    new_count = results["success"]
    skip_count = results["skipped"]
    fail_count = results["failed"]
    overwrite_count = 0
    delete_count = 0

    summary = {
        "operation": "import",
        "data_type": data_type,
        "data_type_name": type_names.get(data_type, data_type),
        "dry_run": dry_run,
        "source_file": file_path,
        "summary": {
            "total": results["total"],
            "new": new_count,
            "overwrite": overwrite_count,
            "skipped": skip_count,
            "failed": fail_count,
            "deleted": delete_count,
        },
        "error_types": results["error_types"],
        "errors": results["errors"],
        "new_ids": [item.get("id") for item in valid_items],
    }

    if summary_json:
        print_info("")
        print_info("=== JSON 变更摘要 ===")
        print(json.dumps(summary, ensure_ascii=False, indent=2))

    if not dry_run and valid_items:
        save_map = {
            "teams": (ctx.db.load_teams, ctx.db.save_teams),
            "players": (ctx.db.load_players, ctx.db.save_players),
            "matches": (ctx.db.load_matches, ctx.db.save_matches),
            "schedules": (ctx.db.load_schedules, ctx.db.save_schedules),
        }
        load_func, save_func = save_map[data_type]
        existing = load_func()
        combined = existing + valid_items
        save_func(combined)

        if data_type == "matches":
            schedules = ctx.db.load_schedules()
            sched_ids = {s["id"] for s in schedules}
            for item in valid_items:
                if item["id"] not in sched_ids:
                    sched_item = {k: v for k, v in item.items()
                                  if k not in ["mvp", "duration", "notes", "type"]}
                    sched_item.setdefault("status", "scheduled")
                    sched_item.setdefault("score_a", 0)
                    sched_item.setdefault("score_b", 0)
                    sched_item.setdefault("maps", [])
                    schedules.append(sched_item)
            ctx.db.save_schedules(schedules)

        if data_type == "schedules":
            matches = ctx.db.load_matches()
            match_ids = {m["id"] for m in matches}
            for item in valid_items:
                if item["id"] not in match_ids:
                    match_item = dict(item)
                    match_item.setdefault("mvp", "")
                    match_item.setdefault("duration", "")
                    match_item.setdefault("notes", "")
                    match_item.setdefault("type", "official")
                    matches.append(match_item)
            ctx.db.save_matches(matches)

        settings = ctx.db.load_settings()
        new_ids = [item.get("id") for item in valid_items]
        detail = f"导入 {len(valid_items)} 条 {data_type}，来自 {file_path}"
        log_operation(ctx.db, settings, "import", data_type, new_ids, detail,
                      after_data=valid_items[:])

        print_success("")
        print_success(f"导入完成，成功 {results['success']} 条。")
    elif dry_run:
        print_info("")
        print_info("试运行模式，未实际保存数据。去掉 --dry-run 参数以实际导入。")


@report_cmd.command("import-preview")
@click.argument("data_type", type=click.Choice(["matches", "teams", "players", "schedules", "all"]))
@click.argument("file_path", type=click.Path(exists=True))
@click.option("--format", "-f", "input_format", default="json",
              type=click.Choice(["json", "csv"]),
              help="输入文件格式")
@pass_context
def report_import_preview(ctx, data_type, file_path, input_format):
    """导入前预检，查看校验结果"""
    type_names = {
        "teams": "队伍",
        "players": "选手",
        "matches": "比赛",
        "schedules": "赛程",
    }

    if data_type == "all":
        all_data = _read_import_file(file_path, input_format)
        if all_data is None:
            return
        if not isinstance(all_data, dict):
            print_error("all 模式下 JSON 必须是对象，包含 teams/players/matches/schedules 键")
            return

        summary = []
        total_success = 0
        total_failed = 0
        total_skipped = 0

        team_items = all_data.get("teams", [])
        team_valid, team_res = _validate_import_data(ctx, "teams", team_items)
        extra_team_ids = [t["id"] for t in team_valid]

        extra_tournament_ids = []

        for dt in ["teams", "players", "matches", "schedules"]:
            items = all_data.get(dt, [])
            if not items:
                continue
            if dt == "teams":
                _, res = team_valid, team_res
            else:
                _, res = _validate_import_data(
                    ctx, dt, items,
                    extra_team_ids=extra_team_ids,
                    extra_tournament_ids=extra_tournament_ids,
                )
            summary.append((type_names[dt], res))
            total_success += res["success"]
            total_failed += res["failed"]
            total_skipped += res["skipped"]

        print_table(
            "导入预检汇总 - 全部类型",
            ["数据类型", "总数", "可导入", "失败", "跳过"],
            [[name, str(r["total"]), str(r["success"]), str(r["failed"]), str(r["skipped"])]
             for name, r in summary] + [
                ["合计", str(sum(r["total"] for _, r in summary)),
                 str(total_success), str(total_failed), str(total_skipped)]
            ],
            table_style=ctx.table_style,
        )

        if total_failed > 0:
            print_warning("")
            print_warning(f"存在 {total_failed} 条校验失败的数据，请修正后再导入。")
        else:
            print_success("")
            print_success("校验全部通过！可以正式导入。")
        return

    data = _read_import_file(file_path, input_format)
    if data is None:
        return

    if not data:
        print_info("文件中没有数据")
        return

    _, results = _validate_import_data(ctx, data_type, data)

    title = f"导入预检 - {type_names.get(data_type, data_type)}"
    _print_import_results(title, results, ctx.table_style)

    if results["failed"] > 0:
        print_warning("")
        print_warning(f"存在 {results['failed']} 条校验失败的数据，请修正后再导入。")
    else:
        print_success("")
        print_success("校验全部通过！可以正式导入。")


def _read_import_file(file_path, input_format):
    """读取导入文件，返回数据列表或 None（失败时）"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            if input_format == "json":
                import json
                data = json.load(f)
                return data
            else:
                import csv
                reader = csv.DictReader(f)
                return list(reader)
    except Exception as e:
        print_error(f"读取文件失败: {e}")
        return None


@report_cmd.command("backup")
@click.option("--output", "-o", default="", help="备份文件路径")
@pass_context
def report_backup(ctx, output):
    """备份全部数据到文件"""
    import json
    from datetime import datetime as dt

    backup_data = {
        "version": "1.0",
        "created_at": dt.now().strftime("%Y-%m-%d %H:%M:%S"),
        "data": {
            "teams": ctx.db.load_teams(),
            "players": ctx.db.load_players(),
            "tournaments": ctx.db.load_tournaments(),
            "matches": ctx.db.load_matches(),
            "schedules": ctx.db.load_schedules(),
            "scrims": ctx.db.load_scrims(),
            "reminders": ctx.db.load_reminders(),
            "settings": ctx.db.load_settings(),
        },
        "summary": {},
    }

    summary = {}
    for key, value in backup_data["data"].items():
        if isinstance(value, list):
            summary[key] = len(value)
        elif isinstance(value, dict):
            summary[key] = len(value)
        else:
            summary[key] = 1
    backup_data["summary"] = summary

    if not output:
        timestamp = dt.now().strftime("%Y%m%d_%H%M%S")
        output = f"esports_backup_{timestamp}.json"

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(backup_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print_error(f"备份失败: {e}")
        return

    type_names = {
        "teams": "队伍",
        "players": "选手",
        "tournaments": "赛事",
        "matches": "比赛",
        "schedules": "赛程",
        "scrims": "训练赛",
        "reminders": "提醒",
        "settings": "配置",
    }

    rows = []
    for key, count in summary.items():
        rows.append([type_names.get(key, key), str(count)])

    print_table("备份完成 - 数据摘要", ["数据类型", "数量"], rows, table_style=ctx.table_style)
    print_success("")
    print_success(f"备份已保存到: {output_path.resolve()}")


@report_cmd.command("restore")
@click.argument("backup_file", type=click.Path(exists=True))
@click.option("--type", "-t", "restore_type", default="all",
              type=click.Choice(["all", "teams", "players", "tournaments",
                                 "matches", "schedules", "scrims", "settings"]),
              help="只恢复指定类型的数据")
@click.option("--dry-run", is_flag=True, help="试运行，显示恢复预览")
@click.option("--yes", "-y", is_flag=True, help="跳过确认，直接恢复")
@click.option("--summary-json", is_flag=True, help="输出JSON格式的变更摘要")
@pass_context
def report_restore(ctx, backup_file, restore_type, dry_run, yes, summary_json):
    """从备份文件恢复数据"""
    import json

    try:
        with open(backup_file, "r", encoding="utf-8") as f:
            backup_data = json.load(f)
    except Exception as e:
        print_error(f"读取备份文件失败: {e}")
        return

    if "data" not in backup_data:
        print_error("备份文件格式不正确：缺少 data 字段")
        return

    data = backup_data.get("data", {})
    created_at = backup_data.get("created_at", "未知")
    version = backup_data.get("version", "1.0")

    type_names = {
        "teams": "队伍",
        "players": "选手",
        "tournaments": "赛事",
        "matches": "比赛",
        "schedules": "赛程",
        "scrims": "训练赛",
        "reminders": "提醒",
        "settings": "配置",
    }

    if restore_type == "all":
        target_types = [k for k in type_names if k in data]
    else:
        target_types = [restore_type]
        if restore_type not in data:
            print_error(f"备份文件中不包含 {type_names.get(restore_type, restore_type)} 数据")
            return

    per_type_stats = []
    rows = []
    total_new = 0
    total_overwrite = 0
    total_delete = 0

    for t in target_types:
        current_count = 0
        current_ids = set()
        load_func = getattr(ctx.db, f"load_{t}", None)
        if load_func:
            current = load_func()
            if isinstance(current, list):
                current_count = len(current)
                current_ids = {item.get("id") for item in current if item.get("id")}
            elif isinstance(current, dict):
                current_count = len(current)

        new_data = data[t]
        new_count = len(new_data) if isinstance(new_data, (list, dict)) else 1

        new_ids = set()
        if isinstance(new_data, list):
            new_ids = {item.get("id") for item in new_data if item.get("id")}
        elif isinstance(new_data, dict):
            new_ids = set(new_data.keys())

        overwrite_count = len(current_ids & new_ids)
        new_only_count = len(new_ids - current_ids)
        delete_count = len(current_ids - new_ids)

        total_new += new_only_count
        total_overwrite += overwrite_count
        total_delete += delete_count

        op = "替换" if new_count > 0 else "清空"
        rows.append([
            type_names.get(t, t),
            str(current_count),
            str(new_count),
            f"+{new_only_count}/={overwrite_count}/-{delete_count}",
            op,
        ])

        per_type_stats.append({
            "type": t,
            "type_name": type_names.get(t, t),
            "current_count": current_count,
            "backup_count": new_count,
            "new": new_only_count,
            "overwrite": overwrite_count,
            "deleted": delete_count,
        })

    print_table(
        f"恢复预览 - {backup_file}",
        ["数据类型", "当前数量", "备份数量", "新增/覆盖/删除", "操作"],
        rows,
        table_style=ctx.table_style,
    )

    print_info(f"备份版本: v{version}")
    print_info(f"创建时间: {created_at}")
    print_info(f"变更汇总: 新增 {total_new} 条，覆盖 {total_overwrite} 条，删除 {total_delete} 条")

    if summary_json:
        summary = {
            "operation": "restore",
            "backup_file": backup_file,
            "backup_version": version,
            "backup_created_at": created_at,
            "restore_type": restore_type,
            "dry_run": dry_run,
            "summary": {
                "new": total_new,
                "overwrite": total_overwrite,
                "deleted": total_delete,
            },
            "per_type": per_type_stats,
        }
        print_info("")
        print_info("=== JSON 变更摘要 ===")
        print(json.dumps(summary, ensure_ascii=False, indent=2))

    if dry_run:
        print_info("")
        print_info("试运行模式，未实际恢复数据。去掉 --dry-run 参数以实际恢复。")
        return

    if not yes:
        print_warning("")
        print_warning("此操作将覆盖当前数据，不可撤销！")
        click.confirm("确认要继续恢复吗？", abort=True)

    save_map = {
        "teams": (ctx.db.load_teams, ctx.db.save_teams),
        "players": (ctx.db.load_players, ctx.db.save_players),
        "tournaments": (ctx.db.load_tournaments, ctx.db.save_tournaments),
        "matches": (ctx.db.load_matches, ctx.db.save_matches),
        "schedules": (ctx.db.load_schedules, ctx.db.save_schedules),
        "scrims": (ctx.db.load_scrims, ctx.db.save_scrims),
        "reminders": (ctx.db.load_reminders, ctx.db.save_reminders),
        "settings": (ctx.db.load_settings, ctx.db.save_settings),
    }

    before_restore = {}
    for t in target_types:
        if t in save_map:
            load_func, _ = save_map[t]
            before_restore[t] = load_func()

    for t in target_types:
        if t in save_map:
            _, save_func = save_map[t]
            save_func(data[t])

    settings = ctx.db.load_settings()
    detail = f"恢复 {len(target_types)} 类数据，备份: {backup_file}, 类型: {restore_type}"
    log_operation(ctx.db, settings, "restore", "system", target_types, detail,
                  before_data=before_restore,
                  after_data={t: data[t] for t in target_types if t in data})

    print_success("")
    print_success(f"数据恢复完成！已恢复 {len(target_types)} 类数据。")


def _diff_data_type(current_list, backup_list, name_field="name"):
    """对比单类型数据，返回 (added, removed, modified)

    modified 每项格式: {"id": ..., "name": ..., "changes": [{"field":..., "old":..., "new":...}]}
    """
    current_by_id = {item["id"]: item for item in current_list if item.get("id")}
    backup_by_id = {item["id"]: item for item in backup_list if item.get("id")}

    current_ids = set(current_by_id.keys())
    backup_ids = set(backup_by_id.keys())

    added_ids = current_ids - backup_ids
    removed_ids = backup_ids - current_ids
    common_ids = current_ids & backup_ids

    added = [current_by_id[i] for i in sorted(added_ids)]
    removed = [backup_by_id[i] for i in sorted(removed_ids)]

    modified = []
    for item_id in sorted(common_ids):
        cur = current_by_id[item_id]
        bak = backup_by_id[item_id]
        all_keys = set(cur.keys()) | set(bak.keys())
        changes = []
        for key in sorted(all_keys):
            old_val = bak.get(key)
            new_val = cur.get(key)
            if old_val != new_val:
                changes.append({"field": key, "old": old_val, "new": new_val})
        if changes:
            modified.append({
                "id": item_id,
                "name": cur.get(name_field, item_id),
                "changes": changes,
            })

    return added, removed, modified


def _diff_to_dict(current_data, backup_data, type_config):
    """生成完整 diff 结果字典"""
    result = {}
    for data_type, name_field in type_config.items():
        cur = current_data.get(data_type, [])
        bak = backup_data.get(data_type, [])
        added, removed, modified = _diff_data_type(cur, bak, name_field)
        result[data_type] = {
            "added": added,
            "removed": removed,
            "modified": modified,
            "counts": {
                "added": len(added),
                "removed": len(removed),
                "modified": len(modified),
            },
        }
    return result


@report_cmd.command("diff")
@click.argument("backup_file", type=click.Path(exists=True))
@click.option("--type", "-t", "diff_type", default="all",
              type=click.Choice(["all", "teams", "players", "tournaments", "matches", "schedules"]),
              help="只对比指定类型")
@click.option("--output", "-O", "output_path", default="", help="导出到文件 (.md 或 .json)")
@pass_context
def report_diff(ctx, backup_file, diff_type, output_path):
    """数据审计对比：当前数据 vs 备份文件 diff"""
    import json

    type_names = {
        "teams": "队伍",
        "players": "选手",
        "tournaments": "赛事",
        "matches": "比赛",
        "schedules": "赛程",
    }
    name_fields = {
        "teams": "name",
        "players": "name",
        "tournaments": "name",
        "matches": "id",
        "schedules": "id",
    }

    try:
        with open(backup_file, "r", encoding="utf-8") as f:
            backup_data = json.load(f)
    except Exception as e:
        print_error(f"读取备份文件失败: {e}")
        return

    if "data" not in backup_data:
        print_error("备份文件格式不正确：缺少 data 字段")
        return

    backup = backup_data.get("data", {})
    created_at = backup_data.get("created_at", "未知")

    current = {
        "teams": ctx.db.load_teams(),
        "players": ctx.db.load_players(),
        "tournaments": ctx.db.load_tournaments(),
        "matches": ctx.db.load_matches(),
        "schedules": ctx.db.load_schedules(),
    }

    if diff_type == "all":
        target_types = ["teams", "players", "tournaments", "matches", "schedules"]
    else:
        target_types = [diff_type]

    diff_result = _diff_to_dict(current, backup, {t: name_fields[t] for t in target_types})

    total_added = sum(diff_result[t]["counts"]["added"] for t in target_types)
    total_removed = sum(diff_result[t]["counts"]["removed"] for t in target_types)
    total_modified = sum(diff_result[t]["counts"]["modified"] for t in target_types)

    if not output_path or not output_path.endswith(".json"):
        print_info(f"备份文件: {backup_file}")
        print_info(f"备份时间: {created_at}")
        print_info("")

        summary_rows = []
        for t in target_types:
            c = diff_result[t]["counts"]
            summary_rows.append([
                type_names.get(t, t),
                str(len(current.get(t, []))),
                str(len(backup.get(t, []))),
                f"+{c['added']}",
                f"-{c['removed']}",
                f"~{c['modified']}",
            ])

        print_table(
            "数据对比汇总",
            ["数据类型", "当前数量", "备份数量", "新增", "删除", "修改"],
            summary_rows + [
                ["合计",
                 str(sum(len(current.get(t, [])) for t in target_types)),
                 str(sum(len(backup.get(t, [])) for t in target_types)),
                 f"+{total_added}", f"-{total_removed}", f"~{total_modified}"]
            ],
            table_style=ctx.table_style,
        )

        for t in target_types:
            dr = diff_result[t]
            if dr["counts"]["added"] == 0 and dr["counts"]["removed"] == 0 and dr["counts"]["modified"] == 0:
                continue

            print_info("")
            print_info(f"=== {type_names.get(t, t)} 详细变更 ===")

            if dr["added"]:
                print_success(f"  新增 {len(dr['added'])} 条:")
                for item in dr["added"]:
                    nf = name_fields.get(t, "name")
                    print_success(f"    + {item.get(nf, item.get('id'))} ({item.get('id')})")

            if dr["removed"]:
                print_error(f"  删除 {len(dr['removed'])} 条:")
                for item in dr["removed"]:
                    nf = name_fields.get(t, "name")
                    print_error(f"    - {item.get(nf, item.get('id'))} ({item.get('id')})")

            if dr["modified"]:
                print_warning(f"  修改 {len(dr['modified'])} 条:")
                for m in dr["modified"]:
                    print_warning(f"    ~ {m['name']} ({m['id']})")
                    for ch in m["changes"][:5]:
                        old_str = str(ch["old"]) if ch["old"] is not None else "(空)"
                        new_str = str(ch["new"]) if ch["new"] is not None else "(空)"
                        if len(old_str) > 30:
                            old_str = old_str[:30] + "..."
                        if len(new_str) > 30:
                            new_str = new_str[:30] + "..."
                        print_warning(f"      · {ch['field']}: {old_str} → {new_str}")
                    if len(m["changes"]) > 5:
                        print_warning(f"      · ... 还有 {len(m['changes']) - 5} 处变更")

    if output_path:
        out_path = Path(output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        if output_path.endswith(".json"):
            export_data = {
                "backup_file": backup_file,
                "backup_created_at": created_at,
                "diff_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "summary": {
                    "added": total_added,
                    "removed": total_removed,
                    "modified": total_modified,
                },
                "types": {},
            }
            for t in target_types:
                export_data["types"][t] = {
                    "name": type_names.get(t, t),
                    **diff_result[t],
                }

            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            print_success("")
            print_success(f"JSON 对比报告已导出到: {out_path.resolve()}")

        elif output_path.endswith(".md"):
            lines = []
            lines.append(f"# 数据审计对比报告")
            lines.append("")
            lines.append(f"- 备份文件: `{backup_file}`")
            lines.append(f"- 备份时间: {created_at}")
            lines.append(f"- 对比时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            lines.append("")
            lines.append("## 汇总")
            lines.append("")
            lines.append("| 数据类型 | 当前数量 | 备份数量 | 新增 | 删除 | 修改 |")
            lines.append("|----------|----------|----------|------|------|------|")
            for t in target_types:
                c = diff_result[t]["counts"]
                lines.append(f"| {type_names.get(t, t)} | {len(current.get(t, []))} | {len(backup.get(t, []))} | {c['added']} | {c['removed']} | {c['modified']} |")
            lines.append(f"| 合计 | {sum(len(current.get(t, [])) for t in target_types)} | {sum(len(backup.get(t, [])) for t in target_types)} | {total_added} | {total_removed} | {total_modified} |")
            lines.append("")

            for t in target_types:
                dr = diff_result[t]
                if dr["counts"]["added"] == 0 and dr["counts"]["removed"] == 0 and dr["counts"]["modified"] == 0:
                    continue

                lines.append(f"## {type_names.get(t, t)}")
                lines.append("")

                if dr["added"]:
                    lines.append(f"### 新增 ({len(dr['added'])})")
                    lines.append("")
                    for item in dr["added"]:
                        nf = name_fields.get(t, "name")
                        lines.append(f"- **{item.get(nf, item.get('id'))}** (`{item.get('id')}`)")
                    lines.append("")

                if dr["removed"]:
                    lines.append(f"### 删除 ({len(dr['removed'])})")
                    lines.append("")
                    for item in dr["removed"]:
                        nf = name_fields.get(t, "name")
                        lines.append(f"- ~~{item.get(nf, item.get('id'))}~~ (`{item.get('id')}`)")
                    lines.append("")

                if dr["modified"]:
                    lines.append(f"### 修改 ({len(dr['modified'])})")
                    lines.append("")
                    for m in dr["modified"]:
                        lines.append(f"#### {m['name']} (`{m['id']}`)")
                        lines.append("")
                        lines.append("| 字段 | 旧值 | 新值 |")
                        lines.append("|------|------|------|")
                        for ch in m["changes"]:
                            old_str = str(ch["old"]) if ch["old"] is not None else "_(空)_"
                            new_str = str(ch["new"]) if ch["new"] is not None else "_(空)_"
                            lines.append(f"| {ch['field']} | {old_str} | {new_str} |")
                        lines.append("")

            with open(out_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            print_success("")
            print_success(f"Markdown 对比报告已导出到: {out_path.resolve()}")

        else:
            print_error("不支持的导出格式，请使用 .md 或 .json 后缀")


@report_cmd.command("logs")
@click.option("--account", "-A", default="", help="按账号筛选")
@click.option("--data-type", "-d", "data_type", default="", help="按数据类型筛选")
@click.option("--operation", "-o", default="", help="按操作类型筛选")
@click.option("--since", default="", help="起始时间 (YYYY-MM-DD)")
@click.option("--until", default="", help="截止时间 (YYYY-MM-DD)")
@click.option("--limit", "-n", type=int, default=50, help="显示条数 (默认50)")
@click.option("--output", "-O", "output_path", default="", help="导出到文件 (.md 或 .json)")
@pass_context
def report_logs(ctx, account, data_type, operation, since, until, limit, output_path):
    """查看操作日志（支持筛选和导出）"""
    logs = ctx.db.load_operation_logs()

    if account:
        logs = [l for l in logs if l.get("account") == account or account in l.get("account_name", "")]
    if data_type:
        logs = [l for l in logs if l.get("data_type") == data_type]
    if operation:
        logs = [l for l in logs if l.get("operation") == operation]
    if since:
        logs = [l for l in logs if l.get("timestamp", "") >= since]
    if until:
        until_full = until + " 23:59:59"
        logs = [l for l in logs if l.get("timestamp", "") <= until_full]

    logs = list(reversed(logs))

    if limit and limit > 0:
        logs = logs[:limit]

    if not logs:
        print_info("暂无符合条件的操作日志")
        return

    if output_path:
        output_path = os.path.abspath(output_path)
        if output_path.endswith(".json"):
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(logs, f, ensure_ascii=False, indent=2)
            print_success(f"日志已导出到 {output_path} ({len(logs)} 条)")
        elif output_path.endswith(".md"):
            md_content = _generate_logs_markdown(logs)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(md_content)
            print_success(f"日志已导出到 {output_path} ({len(logs)} 条)")
        else:
            print_error("只支持 .json 或 .md 格式")
        return

    rows = []
    for log in logs:
        data_ids = log.get("data_ids", [])
        id_str = ", ".join(str(x) for x in data_ids[:3])
        if len(data_ids) > 3:
            id_str += f" 等{len(data_ids)}条"
        rows.append([
            log.get("id", "-"),
            log.get("timestamp", "-"),
            log.get("account_name", log.get("account", "-")),
            log.get("operation", "-"),
            log.get("data_type", "-"),
            id_str or "-",
            log.get("details", "")[:40],
        ])

    print_table(
        "操作日志",
        ["日志ID", "时间", "账号", "操作", "数据类型", "数据ID", "详情"],
        rows,
        table_style=ctx.table_style,
    )
    print_info(f"共 {len(logs)} 条记录")


def _generate_logs_markdown(logs):
    lines = []
    lines.append("# 操作日志\n")
    lines.append(f"**总记录数**: {len(logs)}\n")
    lines.append("## 日志列表\n")
    lines.append("| 日志ID | 时间 | 账号 | 操作 | 数据类型 | 数据ID | 详情 |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- |")

    for log in logs:
        data_ids = log.get("data_ids", [])
        id_str = ", ".join(str(x) for x in data_ids)
        details = (log.get("details", "") or "").replace("|", "\\|")
        lines.append(
            f"| {log.get('id', '-')} "
            f"| {log.get('timestamp', '-')} "
            f"| {log.get('account_name', log.get('account', '-'))} "
            f"| {log.get('operation', '-')} "
            f"| {log.get('data_type', '-')} "
            f"| {id_str} "
            f"| {details} |"
        )

    return "\n".join(lines) + "\n"


@report_cmd.command("undo-preview")
@click.argument("log_id")
@pass_context
def report_undo_preview(ctx, log_id):
    """撤销预览：查看手动撤销某条操作需要改回哪些数据（只读，不执行撤销）"""
    logs = ctx.db.load_operation_logs()

    log_entry = None
    for log in logs:
        if log.get("id") == log_id:
            log_entry = log
            break

    if not log_entry:
        print_error(f"未找到日志: {log_id}")
        return

    op = log_entry.get("operation", "")
    data_type = log_entry.get("data_type", "")
    before = log_entry.get("before_data")
    after = log_entry.get("after_data")

    type_names = {
        "teams": "队伍",
        "players": "选手",
        "tournaments": "赛事",
        "matches": "比赛",
        "schedules": "赛程",
    }

    print_info(f"日志ID: {log_entry.get('id')}")
    print_info(f"操作时间: {log_entry.get('timestamp')}")
    print_info(f"操作账号: {log_entry.get('account_name', log_entry.get('account'))}")
    print_info(f"操作类型: {op}")
    print_info(f"数据类型: {type_names.get(data_type, data_type)}")
    print_info(f"涉及数据ID: {', '.join(str(x) for x in log_entry.get('data_ids', []))}")
    print_info(f"详情: {log_entry.get('details', '')}")
    print_info("")
    print_info("=" * 50)
    print_warning("撤销预览（只读，不会执行任何修改）")
    print_info("=" * 50)
    print_info("")

    if before is None and after is None:
        print_warning("该日志没有记录变更前后数据，无法生成撤销预览。")
        print_info("提示：较早的日志可能未记录详细变更数据。")
        return

    if op == "create":
        print_warning("【撤销操作】删除以下新建的数据:")
        if isinstance(after, dict):
            print_info(f"  - ID: {after.get('id', '?')}")
            name = after.get("name") or after.get("team_a_id", "") + " vs " + after.get("team_b_id", "")
            print_info(f"    名称: {name}")
        elif isinstance(after, list):
            for item in after:
                name = item.get("name", item.get("id", "?"))
                print_info(f"  - {name} ({item.get('id', '?')})")
        print_info("")
        print_warning("注意：删除后相关引用（如比赛引用的队伍）可能会失效。")

    elif op in ("edit", "score_update", "map_result"):
        print_warning("【撤销操作】将以下字段改回原值:")
        print_info("")

        if isinstance(before, dict) and isinstance(after, dict):
            all_keys = set(before.keys()) | set(after.keys())
            changes = []
            for key in sorted(all_keys):
                old_val = before.get(key)
                new_val = after.get(key)
                if old_val != new_val:
                    changes.append((key, old_val, new_val))

            if not changes:
                print_info("  （未检测到字段变化）")
            else:
                rows = []
                for field, old_val, new_val in changes:
                    old_str = str(old_val) if old_val is not None else "(空)"
                    new_str = str(new_val) if new_val is not None else "(空)"
                    if field == "maps" and isinstance(old_val, list):
                        old_str = f"{len(old_val)} 张地图"
                        new_str = f"{len(new_val)} 张地图"
                    if len(old_str) > 40:
                        old_str = old_str[:40] + "..."
                    if len(new_str) > 40:
                        new_str = new_str[:40] + "..."
                    rows.append([field, old_str, new_str])

                print_table(
                    "变更字段对比",
                    ["字段", "当前值（变更后）", "原值（撤销后）"],
                    rows,
                    table_style=ctx.table_style,
                )
        print_info("")
        print_warning("注意：手动撤销时，请确保将对应字段改回原值。")

    elif op == "import":
        print_warning("【撤销操作】删除以下导入的数据:")
        print_info("")

        if isinstance(after, list):
            for item in after:
                name = item.get("name", item.get("id", "?"))
                print_info(f"  - {name} ({item.get('id', '?')})")
        elif isinstance(after, dict):
            for dtype, items in after.items():
                if isinstance(items, list) and items:
                    print_info(f"  [{type_names.get(dtype, dtype)}]")
                    for item in items[:10]:
                        name = item.get("name", item.get("id", "?"))
                        print_info(f"    - {name} ({item.get('id', '?')})")
                    if len(items) > 10:
                        print_info(f"    ... 还有 {len(items) - 10} 条")

        print_info("")
        print_warning("注意：删除导入数据前，请确认没有其他数据依赖这些记录。")

    elif op == "restore":
        print_warning("【撤销操作】将以下类型数据恢复到恢复前的状态:")
        print_info("")

        if isinstance(before, dict):
            for dtype, data in before.items():
                count = len(data) if isinstance(data, list) else 1
                print_info(f"  - {type_names.get(dtype, dtype)}: 恢复为 {count} 条记录")

        print_info("")
        print_warning("注意：撤销恢复 = 重新执行恢复操作，但使用恢复前的旧数据。")
        print_warning("建议：使用 `report backup` 先备份当前数据，再考虑是否撤销。")

    else:
        print_info(f"操作类型 '{op}' 的撤销预览暂不支持详细分析。")
        if before is not None:
            print_info("变更前数据已记录，可手动查看 before_data 字段。")

    print_info("")
    print_info("=" * 50)
    print_info("提示：这是只读预览，系统不会自动执行撤销操作。")
    print_info("如需撤销，请根据上述说明手动执行相应命令。")
    print_info("=" * 50)


@report_cmd.command("reminders")
@pass_context
def report_reminders(ctx):
    """查看提醒列表"""
    reminders = ctx.db.load_reminders()
    schedules = ctx.db.load_schedules()
    teams = {t["id"]: t for t in ctx.db.load_teams()}
    tournaments = {t["id"]: t for t in ctx.db.load_tournaments()}

    if not reminders:
        print_info("暂无提醒")
        return

    rows = []
    for r in reminders:
        match_id = r.get("match_id", "")
        match_data = next((s for s in schedules if s.get("id") == match_id), {})

        team_a = teams.get(match_data.get("team_a_id", ""), {}).get("name", "-")
        team_b = teams.get(match_data.get("team_b_id", ""), {}).get("name", "-")
        tour_name = tournaments.get(match_data.get("tournament_id", ""), {}).get("name", "-")

        rows.append([
            r.get("id", "-"),
            r.get("title", "-"),
            match_id,
            f"{team_a} vs {team_b}",
            tour_name,
            r.get("remind_time", "-"),
            r.get("status", "pending"),
        ])

    print_table(
        "提醒列表",
        ["提醒ID", "标题", "比赛ID", "对阵", "赛事", "提醒时间", "状态"],
        rows,
        table_style=ctx.table_style,
    )
