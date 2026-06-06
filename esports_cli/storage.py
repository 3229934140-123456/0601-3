import json
import os
from pathlib import Path
from datetime import datetime, date


def get_data_dir():
    data_dir = Path.home() / ".esports_cli" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_config_dir():
    config_dir = Path.home() / ".esports_cli" / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def load_json(filepath, default=None):
    if default is None:
        default = []
    if not os.path.exists(filepath):
        return default
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return default


def save_json(filepath, data):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def generate_id(prefix=""):
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    import random
    suffix = str(random.randint(1000, 9999))
    return f"{prefix}{timestamp}{suffix}"


def parse_date(date_str):
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%m-%d", "%m/%d"):
        try:
            if fmt in ("%m-%d", "%m/%d"):
                year = date.today().year
                dt = datetime.strptime(f"{year}-{date_str}", f"%Y-{fmt}")
                return dt.date()
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"无法解析日期: {date_str}，支持格式: YYYY-MM-DD, YYYY/MM/DD, MM-DD, MM/DD")


def parse_datetime(datetime_str):
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M"):
        try:
            return datetime.strptime(datetime_str, fmt)
        except ValueError:
            continue
    raise ValueError(f"无法解析时间: {datetime_str}")
