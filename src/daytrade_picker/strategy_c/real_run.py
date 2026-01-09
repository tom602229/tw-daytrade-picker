import datetime as dt
from pathlib import Path

import pandas as pd
import yaml

from .strategy import run_strategy_c


def _parse_date_from_market_filename(p: Path) -> dt.date | None:
    name = p.name
    if not name.startswith("market_") or not name.endswith(".csv"):
        return None
    s = name[len("market_") : -len(".csv")]
    try:
        return dt.datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None


def load_market_history(market_dir: Path, end_date: dt.date, history_days: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    files = list(market_dir.glob("market_*.csv"))
    dated = []
    for f in files:
        d = _parse_date_from_market_filename(f)
        if d is None:
            continue
        if d <= end_date:
            dated.append((d, f))

    dated.sort(key=lambda x: x[0])
    dated = dated[-history_days:]

    if len(dated) == 0:
        raise RuntimeError(f"No market_*.csv found in {market_dir}")

    frames = []
    for d, f in dated:
        df = pd.read_csv(f, encoding="utf-8-sig")
        if "date" in df.columns:
            df = df.rename(columns={"date": "trade_date"})
        df["trade_date"] = pd.to_datetime(df["trade_date"]).dt.date
        frames.append(df)

    daily_price = pd.concat(frames, ignore_index=True)

    # Normalize schema to strategy_c expectations
    keep = {
        "trade_date": "trade_date",
        "stock_id": "stock_id",
        "open": "open",
        "high": "high",
        "low": "low",
        "close": "close",
        "pct_change": "pct_change",
        "volume": "volume",
        "turnover": "turnover",
        "is_limit_up": "is_limit_up",
        "is_limit_down": "is_limit_down",
    }
    for k in list(keep.keys()):
        if k not in daily_price.columns:
            daily_price[k] = pd.NA

    daily_price = daily_price[list(keep.keys())].copy()

    stock_meta = frames[-1][["stock_id", "name", "market"]].copy() if all(c in frames[-1].columns for c in ["stock_id", "name", "market"]) else pd.DataFrame(columns=["stock_id", "stock_name", "market"])
    stock_meta = stock_meta.rename(columns={"name": "stock_name"})

    stock_meta = stock_meta.drop_duplicates(subset=["stock_id"]).reset_index(drop=True)

    return stock_meta, daily_price


def load_themes_mapping(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8-sig")
    if "stock_id" not in df.columns or "themes" not in df.columns:
        raise RuntimeError("themes_mapping.csv must have columns: stock_id,themes")
    df["stock_id"] = df["stock_id"].astype(str).str.strip()
    df["themes"] = df["themes"].astype(str).str.strip()
    df["themes"] = df["themes"].str.split(";").str[0].fillna("UNKNOWN")
    return df


def run_strategy_c_real(
    trade_date: dt.date,
    config_path: Path,
    market_dir: Path,
    themes_mapping_path: Path,
    history_days: int,
    out_dir: Path,
) -> pd.DataFrame:
    cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))

    stock_meta, daily_price = load_market_history(market_dir=market_dir, end_date=trade_date, history_days=history_days)

    themes_map = load_themes_mapping(themes_mapping_path)
    stock_meta = stock_meta.merge(themes_map, on="stock_id", how="left")
    stock_meta["themes"] = stock_meta["themes"].fillna("UNKNOWN")
    stock_meta["industry"] = stock_meta["themes"]

    candidates, _, _, strong = run_strategy_c(
        trade_date=trade_date,
        stock_meta=stock_meta,
        daily_price=daily_price,
        risk_flags=None,
        cfg=cfg,
        sector_mode="themes",
    )

    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / f"strategyC_candidates_{trade_date.isoformat()}.csv"
    xlsx_path = out_dir / f"strategyC_candidates_{trade_date.isoformat()}.xlsx"

    enriched = candidates.merge(stock_meta[["stock_id", "stock_name", "market", "themes"]], on="stock_id", how="left")

    enriched.to_csv(csv_path, index=False, encoding="utf-8-sig")
    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as w:
        enriched.to_excel(w, index=False, sheet_name="StrategyC")
        strong.to_excel(w, index=False, sheet_name="StrongThemes")

    top10 = enriched.head(10)
    cols = ["trade_date", "stock_id", "stock_name", "themes", "leader_id", "score_total", "suggest_entry", "suggest_stop", "shares", "lots_1000"]
    for c in cols:
        if c not in top10.columns:
            top10[c] = pd.NA
    print(top10[cols].to_string(index=False))

    return enriched
