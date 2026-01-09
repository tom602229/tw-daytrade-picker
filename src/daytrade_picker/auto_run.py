import datetime as dt
import time
from pathlib import Path

import yaml

from .pipeline import run_pipeline
from .sources.twse_tpex import fetch_daily_prices_all


def _is_business_day(d: dt.date) -> bool:
    return d.weekday() < 5


def _candidate_dates(today: dt.date, max_lookback_days: int) -> list[dt.date]:
    out: list[dt.date] = []
    d = today
    for _ in range(max_lookback_days + 1):
        if _is_business_day(d):
            out.append(d)
        d = d - dt.timedelta(days=1)
    return out


def pick_latest_available_date(today: dt.date, max_lookback_days: int) -> dt.date | None:
    for d in _candidate_dates(today, max_lookback_days=max_lookback_days):
        px = fetch_daily_prices_all(d)
        if len(px) > 0:
            return d
    return None


def run_auto(config_path: Path, max_lookback_days: int, retries: int, retry_sleep_seconds: int) -> dt.date:
    cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))

    today = dt.date.today()

    for _ in range(max(1, retries + 1)):
        d = pick_latest_available_date(today=today, max_lookback_days=max_lookback_days)
        if d is not None:
            run_pipeline(run_date=d, config_path=config_path)
            return d
        time.sleep(max(1, int(retry_sleep_seconds)))

    raise RuntimeError("No available market data within lookback window")
