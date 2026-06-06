import click
import os
from datetime import datetime
from pathlib import Path

from esports_cli.context import pass_context
from esports_cli.utils import (
    print_table,
    print_success,
    print_error,
    print_info,
    print_panel,
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
    teams = {t["id"]: t for t in ctx.db.load_teams()}
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

    if output_format == "json":
        import json
        content = json.dumps(match_data, ensure_ascii=False, indent=2)
    elif output_format == "md":
        content = _generate_match_report_md(match_data, team_a, team_b, tour, players)
    else:
        content = _generate_match_report_text(match_data, team_a, team_b, tour, players)

    if output:
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
        print_success(f"战报已导出到: {output_path}")
    else:
        print_panel(f"比赛战报 - {match_id}", content)


def _generate_match_report_text(match_data, team_a, team_b, tour, players):
    lines = []
    lines.append("=" * 50)
    lines.append(f"比赛战报: {match_data.get('id', '')}")
    lines.append("=" * 50)
    lines.append("")
    lines.append(f"赛事: {tour.get('name', '-')}")
    lines.append(f"阶段: {match_data.get('stage', '-')}")
    lines.append(f"时间: {match_data.get('datetime', '-')}")
    lines.append(f"赛制: BO{match_data.get('bo', 3)}")
    lines.append(f"状态: {match_data.get('status', '-')}")
    lines.append("")
    lines.append(f"对阵:")
    lines.append(f"  {team_a.get('name', 'TBD')}  vs  {team_b.get('name', 'TBD')}")
    lines.append(f"  比分: {match_data.get('score_a', 0)} : {match_data.get('score_b', 0)}")
    lines.append("")

    if match_data.get("maps"):
        lines.append("-" * 50)
        lines.append("地图详情:")
        lines.append("-" * 50)
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
    lines.append("=" * 50)
    return "\n".join(lines)


def _generate_match_report_md(match_data, team_a, team_b, tour, players):
    lines = []
    lines.append(f"# 比赛战报: {match_data.get('id', '')}")
    lines.append("")
    lines.append("## 基本信息")
    lines.append("")
    lines.append(f"- **赛事**: {tour.get('name', '-')}")
    lines.append(f"- **阶段**: {match_data.get('stage', '-')}")
    lines.append(f"- **时间**: {match_data.get('datetime', '-')}")
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
        lines.append("## 地图详情")
        lines.append("")
        lines.append("| 序号 | 地图 | 队伍A | 队伍B | 胜者 | 时长 |")
        lines.append("|------|------|-------|-------|------|------|")
        for i, mp in enumerate(match_data["maps"], 1):
            winner = team_a.get("name", "A") if mp.get("winner", "").upper() == "A" else team_b.get("name", "B")
            lines.append(f"| {i} | {mp.get('map_name', '-')} | {mp.get('score_a', 0)} | {mp.get('score_b', 0)} | {winner} | {mp.get('duration', '-')} |")
        lines.append("")

    if match_data.get("mvp"):
        lines.append(f"## MVP")
        lines.append("")
        lines.append(f"{match_data['mvp']}")
        lines.append("")

    if match_data.get("notes"):
        lines.append("## 备注")
        lines.append("")
        lines.append(match_data["notes"])
        lines.append("")

    return "\n".join(lines)


@report_cmd.command("team")
@click.argument("team_id")
@click.option("--tournament", "-t", help="赛事ID")
@click.option("--output", "-o", default="", help="输出文件路径")
@pass_context
def report_team(ctx, team_id, tournament, output):
    """生成队伍战绩报告"""
    teams = ctx.db.load_teams()
    matches = ctx.db.load_matches()
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

    for m in team_matches:
        is_a = m.get("team_a_id") == team_id
        s_a = m.get("score_a", 0)
        s_b = m.get("score_b", 0)

        if is_a:
            score_for += s_a
            score_against += s_b
            if s_a > s_b:
                wins += 1
            elif s_a < s_b:
                losses += 1
        else:
            score_for += s_b
            score_against += s_a
            if s_b > s_a:
                wins += 1
            elif s_b < s_a:
                losses += 1

    total = wins + losses
    win_rate = (wins / total * 100) if total > 0 else 0

    lines = []
    lines.append("=" * 60)
    lines.append(f"队伍战绩报告: {team_data.get('name', '')}")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"总场次: {total}")
    lines.append(f"胜场: {wins}")
    lines.append(f"败场: {losses}")
    lines.append(f"胜率: {win_rate:.2f}%")
    lines.append(f"总得分: {score_for}")
    lines.append(f"总失分: {score_against}")
    lines.append(f"净胜分: {score_for - score_against:+d}")
    lines.append("")
    lines.append("-" * 60)
    lines.append("近期比赛:")
    lines.append("-" * 60)

    for m in team_matches[:10]:
        opp_id = m["team_b_id"] if m["team_a_id"] == team_id else m["team_a_id"]
        opp_name = tournaments.get(m.get("tournament_id", ""), {}).get("name", "-")
        is_a = m.get("team_a_id") == team_id
        my_score = m["score_a"] if is_a else m["score_b"]
        opp_score = m["score_b"] if is_a else m["score_a"]
        result = "胜" if my_score > opp_score else "负" if my_score < opp_score else "平"

        lines.append(f"{m.get('date', '')} - BO{m.get('bo', 3)} {result} ({my_score}:{opp_score})")

    content = "\n".join(lines)

    if output:
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
        print_success(f"队伍报告已导出到: {output_path}")
    else:
        print_panel(f"队伍报告 - {team_data.get('name', '')}", content)


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
            m.get("date", "-"),
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
    )
