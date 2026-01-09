import datetime as dt
from pathlib import Path

import pandas as pd
import yaml

from .data import make_demo_market_data
from .strategy import run_strategy_c


def run_demo(trade_date: dt.date, config_path: Path) -> pd.DataFrame:
    cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))

    demo_cfg = cfg.get("demo", {})

    md = make_demo_market_data(
        asof=trade_date,
        num_stocks=int(demo_cfg.get("num_stocks", 220)),
        num_sectors=int(demo_cfg.get("num_sectors", 12)),
        history_days=int(demo_cfg.get("history_days", 40)),
        seed=int(demo_cfg.get("seed", 7)),
    )

    candidates, features, sector_daily, strong_sectors = run_strategy_c(
        trade_date=trade_date,
        stock_meta=md.stock_meta,
        daily_price=md.daily_price,
        risk_flags=None,
        cfg=cfg,
    )

    top10 = candidates.head(10).copy()

    display = top10.merge(md.stock_meta[["stock_id", "stock_name", "industry"]], on="stock_id", how="left")
    cols = [
        "trade_date",
        "stock_id",
        "stock_name",
        "industry",
        "leader_id",
        "sector_id",
        "score_total",
        "score_sector",
        "score_leader",
        "score_follow",
        "suggest_entry",
        "suggest_stop",
        "shares",
        "lots_1000",
    ]
    for c in cols:
        if c not in display.columns:
            display[c] = pd.NA

    display = display[cols]
    print(display.to_string(index=False))

    return candidates
