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
    print_info,
    print_panel,
    format_date,
    format_datetime,
    calculate_win_rate,
    validate_datetime,
    console,
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
@click.option("--output", "-o", default="", help="输出文件路径")
@pass_context
def report_match(ctx, match_id, output_format, output):
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
        }
        content = json.dumps(full_data, ensure_ascii=False, indent=2)
    elif output_format == "md":
        content = _generate_match_report_md(match_data, team_a, team_b, tour,
                                            h2h_matches, h2h_wins_a, h2h_wins_b,
                                            ctx.date_fmt)
    else:
        content = _generate_match_report_text(match_data, team_a, team_b, tour,
                                              h2h_matches, h2h_wins_a, h2h_wins_b,
                                              ctx.date_fmt)

    if output:
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
        print_success(f"战报已导出到: {output_path}")
    else:
        print_panel(f"比赛战报 - {match_id}", content)


def _generate_match_report_text(match_data, team_a, team_b, tour,
                                h2h_matches, h2h_wins_a, h2h_wins_b, date_fmt):
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
                              h2h_matches, h2h_wins_a, h2h_wins_b, date_fmt):
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
@click.option("--format", "-f", "output_format", default="text",
              type=click.Choice(["text", "md", "json"]),
              help="输出格式")
@click.option("--output", "-o", default="", help="输出文件路径")
@pass_context
def report_team(ctx, team_id, tournament, output_format, output):
    """生成队伍战绩报告"""
    teams = ctx.db.load_teams()
    matches = ctx.db.load_matches()
    teams_map = {t["id"]: t for t in teams}
    tournaments = {t["id"]: t for t in ctx.db.load_tournaments()}

    team_data = next((t for t in teams if t.get("id") == team_id), None)
    if not team_data:
        print_error(f"未找到队伍: {team_id}")
        return

    team_matches = []
    for m in matches:
        if m.get("status") != "finished":
            continue
        if tournament and m.get("tournament_id") != tournament:
            continue
        if m.get("team_a_id") != team_id and m.get("team_b_id") != team_id:
            continue
        team_matches.append(m)

    team_matches.sort(key=lambda x: x.get("datetime", ""), reverse=True)

    wins = 0
    losses = 0
    score_for = 0
    score_against = 0
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

    if output_format == "json":
        full_data = {
            "team": team_data,
            "summary": {
                "total_matches": total,
                "wins": wins,
                "losses": losses,
                "win_rate": f"{win_rate:.2f}%",
                "score_for": score_for,
                "score_against": score_against,
                "score_diff": score_for - score_against,
            },
            "recent_form": recent_form[:10],
            "opponent_stats": list(opponent_stats.values()),
            "tournament_stats": list(tournament_stats.values()),
        }
        content = json.dumps(full_data, ensure_ascii=False, indent=2)
    elif output_format == "md":
        content = _generate_team_report_md(team_data, total, wins, losses, win_rate,
                                           score_for, score_against, recent_form,
                                           opponent_stats, tournament_stats, ctx.date_fmt)
    else:
        content = _generate_team_report_text(team_data, total, wins, losses, win_rate,
                                             score_for, score_against, recent_form,
                                             opponent_stats, tournament_stats, ctx.date_fmt)

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
                               opponent_stats, tournament_stats, date_fmt):
    lines = []
    lines.append("=" * 70)
    lines.append(f"队伍战绩报告: {team_data.get('name', '')}")
    lines.append("=" * 70)
    lines.append("")
    lines.append(f"总场次: {total}  胜场: {wins}  败场: {losses}  胜率: {win_rate:.2f}%")
    lines.append(f"总得分: {score_for}  总失分: {score_against}  净胜分: {score_for - score_against:+d}")
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
                             opponent_stats, tournament_stats, date_fmt):
    lines = []
    lines.append(f"# 队伍战绩报告: {team_data.get('name', '')}")
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


@report_cmd.command("import")
@click.argument("data_type", type=click.Choice(["matches", "teams", "players", "schedules"]))
@click.argument("file_path", type=click.Path(exists=True))
@click.option("--format", "-f", "input_format", default="json",
              type=click.Choice(["json", "csv"]),
              help="输入文件格式")
@click.option("--dry-run", is_flag=True, help="试运行，不实际保存")
@pass_context
def report_import(ctx, data_type, file_path, input_format, dry_run):
    """批量导入数据"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            if input_format == "json":
                import json
                data = json.load(f)
                if not isinstance(data, list):
                    print_error("JSON 文件必须是数组格式")
                    return
            else:
                import csv
                reader = csv.DictReader(f)
                data = list(reader)
    except Exception as e:
        print_error(f"读取文件失败: {e}")
        return

    if not data:
        print_info("文件中没有数据")
        return

    required_fields_map = {
        "teams": ["id", "name", "region"],
        "players": ["id", "name", "team_id", "role"],
        "matches": ["id", "tournament_id", "team_a_id", "team_b_id", "datetime"],
        "schedules": ["id", "tournament_id", "team_a_id", "team_b_id", "datetime"],
    }
    required_fields = required_fields_map.get(data_type, [])

    results = {
        "total": len(data),
        "success": 0,
        "failed": 0,
        "skipped": 0,
        "errors": [],
    }

    load_map = {
        "teams": (ctx.db.load_teams, ctx.db.save_teams),
        "players": (ctx.db.load_players, ctx.db.save_players),
        "matches": (ctx.db.load_matches, ctx.db.save_matches),
        "schedules": (ctx.db.load_schedules, ctx.db.save_schedules),
    }
    load_func, save_func = load_map[data_type]
    existing_data = load_func()
    existing_ids = {item.get("id") for item in existing_data}

    new_items = []
    for idx, item in enumerate(data, 1):
        item_id = item.get("id", "")

        if not item_id:
            results["failed"] += 1
            results["errors"].append(f"第 {idx} 条: 缺少 id 字段")
            continue

        if item_id in existing_ids:
            results["skipped"] += 1
            results["errors"].append(f"第 {idx} 条 (ID: {item_id}): ID 已存在，跳过")
            continue

        missing = [f for f in required_fields if not item.get(f)]
        if missing:
            results["failed"] += 1
            results["errors"].append(f"第 {idx} 条 (ID: {item_id}): 缺少字段: {', '.join(missing)}")
            continue

        if data_type in ["matches", "schedules"] and item.get("datetime"):
            valid, _, _ = validate_datetime(item["datetime"])
            if not valid:
                results["failed"] += 1
                results["errors"].append(f"第 {idx} 条 (ID: {item_id}): 日期格式无效: {item['datetime']}")
                continue

        if data_type in ["players"] and item.get("team_id"):
            teams = {t["id"] for t in ctx.db.load_teams()}
            if item["team_id"] not in teams:
                results["failed"] += 1
                results["errors"].append(f"第 {idx} 条 (ID: {item_id}): 队伍不存在: {item['team_id']}")
                continue

        if data_type in ["matches", "schedules"]:
            teams = {t["id"] for t in ctx.db.load_teams()}
            tournaments = {t["id"] for t in ctx.db.load_tournaments()}
            if item.get("tournament_id") and item["tournament_id"] not in tournaments:
                results["failed"] += 1
                results["errors"].append(f"第 {idx} 条 (ID: {item_id}): 赛事不存在: {item['tournament_id']}")
                continue
            if item.get("team_a_id") and item["team_a_id"] not in teams:
                results["failed"] += 1
                results["errors"].append(f"第 {idx} 条 (ID: {item_id}): 队伍A不存在: {item['team_a_id']}")
                continue
            if item.get("team_b_id") and item["team_b_id"] not in teams:
                results["failed"] += 1
                results["errors"].append(f"第 {idx} 条 (ID: {item_id}): 队伍B不存在: {item['team_b_id']}")
                continue

        new_item = dict(item)
        if data_type in ["matches", "schedules"]:
            if "datetime" in new_item and "date" not in new_item:
                valid, norm_dt, date_part = validate_datetime(new_item["datetime"])
                if valid:
                    new_item["datetime"] = norm_dt
                    new_item["date"] = date_part

        new_items.append(new_item)
        results["success"] += 1

    if not dry_run and new_items:
        combined = existing_data + new_items
        save_func(combined)

        if data_type == "matches":
            schedules = ctx.db.load_schedules()
            sched_ids = {s["id"] for s in schedules}
            for item in new_items:
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
            for item in new_items:
                if item["id"] not in match_ids:
                    match_item = dict(item)
                    match_item.setdefault("mvp", "")
                    match_item.setdefault("duration", "")
                    match_item.setdefault("notes", "")
                    match_item.setdefault("type", "official")
                    matches.append(match_item)
            ctx.db.save_matches(matches)

    type_names = {
        "teams": "队伍",
        "players": "选手",
        "matches": "比赛",
        "schedules": "赛程",
    }
    title = f"导入结果 - {type_names.get(data_type, data_type)}"
    if dry_run:
        title += " (试运行)"

    print_table(
        title,
        ["类别", "数量"],
        [
            ["总记录数", str(results["total"])],
            ["成功导入", str(results["success"])],
            ["失败", str(results["failed"])],
            ["跳过(重复)", str(results["skipped"])],
        ],
        table_style=ctx.table_style,
    )

    if results["errors"]:
        print_info("")
        print_info("详细信息:")
        for err in results["errors"][:20]:
            print_info(f"  {err}")
        if len(results["errors"]) > 20:
            print_info(f"  ... 还有 {len(results['errors']) - 20} 条错误")

    if dry_run:
        print_info("")
        print_info("试运行模式，未实际保存数据。去掉 --dry-run 参数以实际导入。")
    else:
        print_success("")
        print_success(f"导入完成，成功 {results['success']} 条。")


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
