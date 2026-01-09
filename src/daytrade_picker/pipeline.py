import datetime as dt
from pathlib import Path

import pandas as pd
import yaml

from .sources.twse_tpex import fetch_daily_prices_all, fetch_institution_net_all
from .storage import persist_daily
from .risk import apply_risk_filter
from .strategies.strategy_a import apply_strategy_a
from .outputs import write_daily_outputs


def run_pipeline(run_date: dt.date, config_path: Path) -> None:
    cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))

    prices = fetch_daily_prices_all(run_date)
    inst = fetch_institution_net_all(run_date)

    df = prices.merge(inst, on=["date", "stock_id"], how="left")

    persist_daily(df, run_date=run_date, cfg=cfg)

    filtered = apply_risk_filter(df, cfg=cfg)

    results = apply_strategy_a(filtered, cfg=cfg)

    write_daily_outputs(results, run_date=run_date, cfg=cfg)
