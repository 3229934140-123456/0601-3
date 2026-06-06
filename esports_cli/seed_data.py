"""生成示例数据，用于演示电竞CLI工具的功能"""
import json
import os
from datetime import datetime, timedelta
from pathlib import Path


def get_data_dir():
    data_dir = Path.home() / ".esports_cli" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_config_dir():
    config_dir = Path.home() / ".esports_cli" / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def save_json(filepath, data):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def generate_sample_data():
    data_dir = get_data_dir()
    config_dir = get_config_dir()

    now = datetime.now()
    today = now.strftime("%Y-%m-%d")

    teams_data = [
        {
            "id": "T001",
            "name": "烈焰战队",
            "short_name": "FLA",
            "region": "华东",
            "coach": "张教练",
            "manager": "王经理",
            "home_stadium": "上海电竞中心",
            "founded": "2020-03-15",
            "stats": {"wins": 42, "losses": 18, "total_matches": 60},
            "achievements": [
                "2023春季赛冠军",
                "2022夏季赛季军",
                "2021年度最佳战队",
            ],
            "roster_changes": [],
        },
        {
            "id": "T002",
            "name": "风暴电竞",
            "short_name": "STO",
            "region": "华北",
            "coach": "李教练",
            "manager": "刘经理",
            "home_stadium": "北京电竞馆",
            "founded": "2019-06-20",
            "stats": {"wins": 38, "losses": 22, "total_matches": 60},
            "achievements": [
                "2023夏季赛亚军",
                "2022春季赛四强",
            ],
            "roster_changes": [],
        },
        {
            "id": "T003",
            "name": "闪电狼",
            "short_name": "WOL",
            "region": "华南",
            "coach": "陈教练",
            "manager": "赵经理",
            "home_stadium": "广州竞技场",
            "founded": "2021-01-10",
            "stats": {"wins": 35, "losses": 25, "total_matches": 60},
            "achievements": [
                "2023春季赛季军",
            ],
            "roster_changes": [],
        },
        {
            "id": "T004",
            "name": "星辰战队",
            "short_name": "STA",
            "region": "西南",
            "coach": "周教练",
            "manager": "吴经理",
            "home_stadium": "成都电竞中心",
            "founded": "2020-08-05",
            "stats": {"wins": 30, "losses": 30, "total_matches": 60},
            "achievements": [],
            "roster_changes": [],
        },
        {
            "id": "T005",
            "name": "猛虎突击队",
            "short_name": "TGR",
            "region": "东北",
            "coach": "孙教练",
            "manager": "郑经理",
            "home_stadium": "沈阳电竞馆",
            "founded": "2019-11-20",
            "stats": {"wins": 28, "losses": 32, "total_matches": 60},
            "achievements": [],
            "roster_changes": [],
        },
        {
            "id": "T006",
            "name": "龙魂战队",
            "short_name": "DRG",
            "region": "华中",
            "coach": "杨教练",
            "manager": "黄经理",
            "home_stadium": "武汉电竞中心",
            "founded": "2022-02-14",
            "stats": {"wins": 25, "losses": 20, "total_matches": 45},
            "achievements": [
                "2023夏季赛黑马战队",
            ],
            "roster_changes": [],
        },
        {
            "id": "T007",
            "name": "夜鹰战队",
            "short_name": "NYG",
            "region": "西北",
            "coach": "胡教练",
            "manager": "林经理",
            "home_stadium": "西安电竞馆",
            "founded": "2021-09-01",
            "stats": {"wins": 22, "losses": 28, "total_matches": 50},
            "achievements": [],
            "roster_changes": [],
        },
        {
            "id": "T008",
            "name": "幻影军团",
            "short_name": "PHN",
            "region": "华东",
            "coach": "何教练",
            "manager": "高经理",
            "home_stadium": "杭州电竞中心",
            "founded": "2020-05-18",
            "stats": {"wins": 32, "losses": 25, "total_matches": 57},
            "achievements": [
                "2022夏季赛亚军",
            ],
            "roster_changes": [],
        },
    ]
    save_json(os.path.join(data_dir, "teams.json"), teams_data)

    players_data = [
        {"id": "P001", "ingame_id": "FireKing", "name": "王磊", "team_id": "T001", "role": "上单", "status": "active",
         "nationality": "中国", "age": 22, "birthday": "2002-05-15", "join_date": "2021-02-10",
         "stats": {"kills": 320, "deaths": 180, "assists": 280, "kda": 3.33, "games_played": 120, "avg_duration": "28min"},
         "achievements": ["2023春季赛最佳上单", "2022年度新秀"]},
        {"id": "P002", "ingame_id": "Blaze", "name": "李明", "team_id": "T001", "role": "打野", "status": "active",
         "nationality": "中国", "age": 21, "birthday": "2003-08-20", "join_date": "2022-01-15",
         "stats": {"kills": 280, "deaths": 150, "assists": 420, "kda": 4.67, "games_played": 110, "avg_duration": "27min"},
         "achievements": ["2023春季赛MVP提名"]},
        {"id": "P003", "ingame_id": "Inferno", "name": "张杰", "team_id": "T001", "role": "中单", "status": "active",
         "nationality": "中国", "age": 23, "birthday": "2001-11-30", "join_date": "2020-06-05",
         "stats": {"kills": 450, "deaths": 200, "assists": 350, "kda": 4.00, "games_played": 130, "avg_duration": "29min"},
         "achievements": ["2023春季赛MVP", "2022最佳中单"]},
        {"id": "P004", "ingame_id": "Ember", "name": "刘洋", "team_id": "T001", "role": "ADC", "status": "active",
         "nationality": "中国", "age": 20, "birthday": "2004-03-12", "join_date": "2023-01-20",
         "stats": {"kills": 380, "deaths": 120, "assists": 180, "kda": 4.67, "games_played": 80, "avg_duration": "30min"},
         "achievements": ["2023夏季赛最佳新人"]},
        {"id": "P005", "ingame_id": "Cinder", "name": "陈浩", "team_id": "T001", "role": "辅助", "status": "active",
         "nationality": "中国", "age": 24, "birthday": "2000-09-08", "join_date": "2020-08-15",
         "stats": {"kills": 80, "deaths": 160, "assists": 520, "kda": 3.75, "games_played": 125, "avg_duration": "28min"},
         "achievements": ["2022最佳辅助提名"]},

        {"id": "P006", "ingame_id": "Thunder", "name": "赵雷", "team_id": "T002", "role": "上单", "status": "active",
         "nationality": "中国", "age": 22, "birthday": "2002-07-25", "join_date": "2021-05-10",
         "stats": {"kills": 290, "deaths": 200, "assists": 250, "kda": 2.70, "games_played": 115, "avg_duration": "29min"},
         "achievements": []},
        {"id": "P007", "ingame_id": "Hurricane", "name": "孙浩", "team_id": "T002", "role": "打野", "status": "active",
         "nationality": "中国", "age": 21, "birthday": "2003-04-18", "join_date": "2022-03-25",
         "stats": {"kills": 260, "deaths": 170, "assists": 380, "kda": 3.76, "games_played": 100, "avg_duration": "28min"},
         "achievements": []},
        {"id": "P008", "ingame_id": "Tempest", "name": "周涛", "team_id": "T002", "role": "中单", "status": "suspended",
         "nationality": "中国", "age": 23, "birthday": "2001-12-05", "join_date": "2020-09-10",
         "stats": {"kills": 380, "deaths": 220, "assists": 320, "kda": 3.18, "games_played": 120, "avg_duration": "27min"},
         "achievements": ["2022夏季赛MVP"],
         "suspension_reason": "违反战队规定",
         "suspension_start": "2024-05-01",
         "suspension_end": "2024-08-01"},
        {"id": "P009", "ingame_id": "Gale", "name": "吴迪", "team_id": "T002", "role": "ADC", "status": "active",
         "nationality": "韩国", "age": 22, "birthday": "2002-10-15", "join_date": "2023-02-28",
         "stats": {"kills": 350, "deaths": 140, "assists": 200, "kda": 3.93, "games_played": 90, "avg_duration": "29min"},
         "achievements": []},
        {"id": "P010", "ingame_id": "Breeze", "name": "郑毅", "team_id": "T002", "role": "辅助", "status": "active",
         "nationality": "中国", "age": 23, "birthday": "2001-06-22", "join_date": "2021-11-05",
         "stats": {"kills": 70, "deaths": 180, "assists": 480, "kda": 3.06, "games_played": 110, "avg_duration": "28min"},
         "achievements": []},

        {"id": "P011", "ingame_id": "AlphaWolf", "name": "黄峰", "team_id": "T003", "role": "上单", "status": "active",
         "nationality": "中国", "age": 21, "birthday": "2003-02-28", "join_date": "2022-08-15",
         "stats": {"kills": 250, "deaths": 190, "assists": 230, "kda": 2.53, "games_played": 95, "avg_duration": "27min"},
         "achievements": []},
        {"id": "P012", "ingame_id": "BetaWolf", "name": "林涛", "team_id": "T003", "role": "打野", "status": "active",
         "nationality": "中国", "age": 22, "birthday": "2002-11-10", "join_date": "2021-07-20",
         "stats": {"kills": 240, "deaths": 160, "assists": 360, "kda": 3.75, "games_played": 100, "avg_duration": "28min"},
         "achievements": []},
        {"id": "P013", "ingame_id": "GammaWolf", "name": "何强", "team_id": "T003", "role": "中单", "status": "active",
         "nationality": "中国", "age": 24, "birthday": "2000-08-05", "join_date": "2020-04-10",
         "stats": {"kills": 400, "deaths": 210, "assists": 340, "kda": 3.52, "games_played": 115, "avg_duration": "29min"},
         "achievements": ["2022春季赛最佳中单"]},
        {"id": "P014", "ingame_id": "DeltaWolf", "name": "罗宇", "team_id": "T003", "role": "ADC", "status": "injured",
         "nationality": "中国", "age": 20, "birthday": "2004-05-20", "join_date": "2023-03-10",
         "stats": {"kills": 300, "deaths": 130, "assists": 170, "kda": 3.62, "games_played": 70, "avg_duration": "30min"},
         "achievements": []},
        {"id": "P015", "ingame_id": "OmegaWolf", "name": "高翔", "team_id": "T003", "role": "辅助", "status": "active",
         "nationality": "中国", "age": 23, "birthday": "2001-03-18", "join_date": "2021-12-01",
         "stats": {"kills": 60, "deaths": 150, "assists": 460, "kda": 3.47, "games_played": 105, "avg_duration": "27min"},
         "achievements": []},

        {"id": "P016", "ingame_id": "Vega", "name": "马超", "team_id": "T004", "role": "上单", "status": "active",
         "nationality": "中国", "age": 22, "birthday": "2002-09-12", "join_date": "2022-02-10",
         "stats": {"kills": 220, "deaths": 200, "assists": 210, "kda": 2.15, "games_played": 85, "avg_duration": "28min"},
         "achievements": []},
        {"id": "P017", "ingame_id": "Sirius", "name": "邓凯", "team_id": "T004", "role": "打野", "status": "active",
         "nationality": "中国", "age": 21, "birthday": "2003-06-25", "join_date": "2022-07-15",
         "stats": {"kills": 200, "deaths": 180, "assists": 300, "kda": 2.78, "games_played": 80, "avg_duration": "27min"},
         "achievements": []},
        {"id": "P018", "ingame_id": "Orion", "name": "曹健", "team_id": "T004", "role": "中单", "status": "active",
         "nationality": "中国", "age": 23, "birthday": "2001-04-08", "join_date": "2021-10-20",
         "stats": {"kills": 340, "deaths": 230, "assists": 290, "kda": 2.74, "games_played": 95, "avg_duration": "29min"},
         "achievements": []},
        {"id": "P019", "ingame_id": "Altair", "name": "谢磊", "team_id": "T004", "role": "ADC", "status": "active",
         "nationality": "中国", "age": 20, "birthday": "2004-08-15", "join_date": "2023-05-01",
         "stats": {"kills": 280, "deaths": 150, "assists": 160, "kda": 2.93, "games_played": 60, "avg_duration": "29min"},
         "achievements": []},
        {"id": "P020", "ingame_id": "Polaris", "name": "韩冰", "team_id": "T004", "role": "辅助", "status": "benched",
         "nationality": "中国", "age": 24, "birthday": "2000-12-20", "join_date": "2020-11-10",
         "stats": {"kills": 50, "deaths": 170, "assists": 400, "kda": 2.65, "games_played": 90, "avg_duration": "28min"},
         "achievements": []},

        {"id": "P021", "ingame_id": "TigerOne", "name": "徐刚", "team_id": "T005", "role": "上单", "status": "active",
         "nationality": "中国", "age": 23, "birthday": "2001-07-05", "join_date": "2020-12-15",
         "stats": {"kills": 270, "deaths": 220, "assists": 240, "kda": 2.32, "games_played": 100, "avg_duration": "27min"},
         "achievements": []},
        {"id": "P022", "ingame_id": "TigerTwo", "name": "朱鹏", "team_id": "T005", "role": "打野", "status": "active",
         "nationality": "中国", "age": 22, "birthday": "2002-10-30", "join_date": "2022-04-20",
         "stats": {"kills": 230, "deaths": 190, "assists": 320, "kda": 2.89, "games_played": 90, "avg_duration": "28min"},
         "achievements": []},
        {"id": "P023", "ingame_id": "TigerThree", "name": "秦超", "team_id": "T005", "role": "中单", "status": "active",
         "nationality": "中国", "age": 24, "birthday": "2000-05-18", "join_date": "2020-07-10",
         "stats": {"kills": 360, "deaths": 240, "assists": 300, "kda": 2.75, "games_played": 105, "avg_duration": "29min"},
         "achievements": []},
        {"id": "P024", "ingame_id": "TigerFour", "name": "尤勇", "team_id": "T005", "role": "ADC", "status": "active",
         "nationality": "中国", "age": 21, "birthday": "2003-01-12", "join_date": "2022-11-25",
         "stats": {"kills": 310, "deaths": 160, "assists": 180, "kda": 3.06, "games_played": 75, "avg_duration": "30min"},
         "achievements": []},
        {"id": "P025", "ingame_id": "TigerFive", "name": "邹明", "team_id": "T005", "role": "辅助", "status": "active",
         "nationality": "中国", "age": 23, "birthday": "2001-08-25", "join_date": "2021-06-15",
         "stats": {"kills": 55, "deaths": 190, "assists": 440, "kda": 2.61, "games_played": 100, "avg_duration": "28min"},
         "achievements": []},
    ]
    save_json(os.path.join(data_dir, "players.json"), players_data)

    tournaments_data = [
        {
            "id": "TPL2024S",
            "name": "2024职业联赛春季赛",
            "short_name": "TPL2024春",
            "type": "regular",
            "season": "Spring",
            "year": 2024,
            "start_date": "2024-03-01",
            "end_date": "2024-05-30",
            "status": "in_progress",
            "teams": ["T001", "T002", "T003", "T004", "T005", "T006", "T007", "T008"],
            "format": "BO3",
            "prize_pool": "5,000,000",
            "description": "全国顶级职业联赛春季赛",
        },
        {
            "id": "TPL2024U",
            "name": "2024夏季杯",
            "short_name": "2024夏杯",
            "type": "cup",
            "season": "Summer",
            "year": 2024,
            "start_date": "2024-07-01",
            "end_date": "2024-08-15",
            "status": "scheduled",
            "teams": ["T001", "T002", "T003", "T004", "T005", "T006", "T007", "T008"],
            "format": "BO5",
            "prize_pool": "3,000,000",
            "description": "夏季杯赛",
        },
        {
            "id": "TPL2023F",
            "name": "2023总决赛",
            "short_name": "S13总决赛",
            "type": "finals",
            "season": "Finals",
            "year": 2023,
            "start_date": "2023-10-01",
            "end_date": "2023-11-15",
            "status": "finished",
            "teams": ["T001", "T002", "T003", "T008"],
            "format": "BO5",
            "prize_pool": "10,000,000",
            "description": "2023年度全球总决赛",
        },
    ]
    save_json(os.path.join(data_dir, "tournaments.json"), tournaments_data)

    schedules_data = []
    match_counter = 1

    tournament_id = "TPL2024S"
    team_ids = ["T001", "T002", "T003", "T004", "T005", "T006", "T007", "T008"]
    base_date = now - timedelta(days=20)

    for week in range(8):
        for day in range(3):
            match_date = base_date + timedelta(days=week * 7 + day)
            if match_date > now + timedelta(days=30):
                continue

            match_date_str = match_date.strftime("%Y-%m-%d")
            match_time = f"{match_date_str} 19:00"

            idx1 = (week + day) % len(team_ids)
            idx2 = (week + day + 3) % len(team_ids)

            is_past = match_date < now
            is_live = (match_date.date() == now.date()) and (now.hour >= 19 and now.hour < 22)

            if is_past:
                status = "finished"
                score_a = 2 if (week + day) % 3 != 0 else 1
                score_b = 1 if (week + day) % 3 != 0 else 2
            elif is_live:
                status = "live"
                score_a = 1
                score_b = 0
            else:
                status = "scheduled"
                score_a = 0
                score_b = 0

            match_id = f"M2024S{match_counter:03d}"

            maps = []
            if status == "finished":
                total_maps = score_a + score_b
                map_names = ["召唤师峡谷", "巨龙之巢", "扭曲丛林"]
                for i in range(total_maps):
                    if i < score_a:
                        winner = "A"
                        s_a, s_b = 1, 0
                    else:
                        winner = "B"
                        s_a, s_b = 0, 1
                    maps.append({
                        "map_name": map_names[i % len(map_names)],
                        "score_a": s_a,
                        "score_b": s_b,
                        "winner": winner,
                        "duration": f"{20 + (i * 5)}min",
                    })

            schedules_data.append({
                "id": match_id,
                "tournament_id": tournament_id,
                "team_a_id": team_ids[idx1],
                "team_b_id": team_ids[idx2],
                "datetime": match_time,
                "date": match_date_str,
                "stage": "常规赛",
                "bo": 3,
                "status": status,
                "score_a": score_a,
                "score_b": score_b,
                "maps": maps,
                "mvp": "" if status != "finished" else f"选手{match_counter}",
                "duration": f"{45 + (match_counter % 3) * 10}min" if status == "finished" else "",
                "type": "official",
            })
            match_counter += 1

    save_json(os.path.join(data_dir, "schedules.json"), schedules_data)

    matches_data = []
    for s in schedules_data:
        match_entry = dict(s)
        match_entry["notes"] = ""
        matches_data.append(match_entry)

    for i in range(5):
        past_date = now - timedelta(days=35 + i * 2)
        past_date_str = past_date.strftime("%Y-%m-%d")
        match_id = f"M2023F{i+1:03d}"
        matches_data.append({
            "id": match_id,
            "tournament_id": "TPL2023F",
            "team_a_id": team_ids[i % len(team_ids)],
            "team_b_id": team_ids[(i + 4) % len(team_ids)],
            "datetime": f"{past_date_str} 20:00",
            "date": past_date_str,
            "stage": "总决赛",
            "bo": 5,
            "status": "finished",
            "score_a": 3 if i % 2 == 0 else 2,
            "score_b": 2 if i % 2 == 0 else 3,
            "maps": [
                {"map_name": "召唤师峡谷", "score_a": 1, "score_b": 0, "winner": "A" if i % 2 == 0 else "B", "duration": "25min"},
                {"map_name": "巨龙之巢", "score_a": 0, "score_b": 1, "winner": "B" if i % 2 == 0 else "A", "duration": "30min"},
                {"map_name": "扭曲丛林", "score_a": 1, "score_b": 0, "winner": "A" if i % 2 == 0 else "B", "duration": "28min"},
                {"map_name": "水晶之痕", "score_a": 0, "score_b": 1, "winner": "B" if i % 2 == 0 else "A", "duration": "32min"},
                {"map_name": "比尔吉沃特", "score_a": 1, "score_b": 0, "winner": "A" if i % 2 == 0 else "B", "duration": "35min"},
            ],
            "mvp": f"总决赛MVP{i+1}",
            "duration": f"{150 + i * 10}min",
            "notes": "",
            "type": "official",
        })

    save_json(os.path.join(data_dir, "matches.json"), matches_data)

    scrims_data = []
    for i in range(10):
        scrim_date = now - timedelta(days=i + 1)
        scrim_date_str = scrim_date.strftime("%Y-%m-%d")
        scrims_data.append({
            "id": f"SCR{i+1:04d}",
            "team_a_id": team_ids[i % len(team_ids)],
            "team_b_id": team_ids[(i + 2) % len(team_ids)],
            "date": scrim_date_str,
            "datetime": f"{scrim_date_str} 20:00",
            "score_a": 2 if i % 2 == 0 else 1,
            "score_b": 1 if i % 2 == 0 else 2,
            "result": "win" if i % 2 == 0 else "lose",
            "notes": f"训练赛 {i+1} - 常规训练" if i % 3 != 0 else "训练赛 - 战术演练",
            "maps": [],
        })
    save_json(os.path.join(data_dir, "scrims.json"), scrims_data)

    reminders_data = [
        {
            "id": "R001",
            "title": "季后赛半决赛提醒",
            "match_id": schedules_data[-1]["id"] if schedules_data else "",
            "remind_time": f"{today} 18:00",
            "status": "pending",
            "notes": "重要比赛，提前准备",
        },
        {
            "id": "R002",
            "title": "训练赛提醒",
            "match_id": "",
            "remind_time": f"{today} 19:30",
            "status": "pending",
            "notes": "明日训练赛确认",
        },
    ]
    save_json(os.path.join(data_dir, "reminders.json"), reminders_data)

    settings = {
        "current_account": "default",
        "accounts": {
            "default": {
                "name": "默认管理员",
                "role": "admin",
                "email": "admin@esports.local",
            },
            "manager_zhang": {
                "name": "张经理",
                "role": "manager",
                "email": "zhang@flames.com",
            },
            "analyst_li": {
                "name": "李分析师",
                "role": "analyst",
                "email": "li@analysis.com",
            },
        },
        "preferences": {
            "default_tournament": "TPL2024S",
            "date_format": "YYYY-MM-DD",
            "table_style": "rich",
            "timezone": "Asia/Shanghai",
        },
    }
    save_json(os.path.join(config_dir, "settings.json"), settings)

    print("✅ 示例数据生成完成！")
    print(f"📁 数据目录: {data_dir}")
    print(f"📁 配置目录: {config_dir}")
    print("")
    print("📊 生成的数据:")
    print(f"  • 赛事: {len(tournaments_data)} 个")
    print(f"  • 队伍: {len(teams_data)} 支")
    print(f"  • 选手: {len(players_data)} 名")
    print(f"  • 赛程: {len(schedules_data)} 场")
    print(f"  • 比赛记录: {len(matches_data)} 场")
    print(f"  • 训练赛: {len(scrims_data)} 场")
    print(f"  • 提醒: {len(reminders_data)} 条")
    print("")
    print("💡 尝试运行: esports dashboard")


if __name__ == "__main__":
    generate_sample_data()
