from __future__ import annotations

import math

import pandas as pd


def apply_universe_filters(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    u = cfg.get("universe", {})

    out = df.copy()

    if u.get("min_turnover") is not None:
        out = out[out["turnover"].fillna(0) >= float(u["min_turnover"])]

    if u.get("min_price") is not None:
        out = out[out["close"].fillna(0) >= float(u["min_price"])]

    if u.get("max_price") is not None:
        out = out[out["close"].fillna(0) <= float(u["max_price"])]

    for col in ["is_disposed", "is_full_margin", "is_blacklist"]:
        if col in out.columns:
            out = out[out[col].fillna(False) == False]  # noqa: E712

    return out


def suggest_stop(prev_low: float | None, buffer_pct: float) -> float | None:
    if prev_low is None or not math.isfinite(prev_low):
        return None
    return float(prev_low * (1.0 - buffer_pct))


def size_suggestion(capital: float, risk_per_trade: float, entry: float | None, stop: float | None, max_position_pct: float) -> dict:
    if entry is None or stop is None or entry <= 0 or stop <= 0 or stop >= entry:
        return {"position_value": None, "shares": None, "lots_1000": None}

    risk_budget = capital * risk_per_trade
    risk_per_share = entry - stop

    shares_by_risk = math.floor(risk_budget / risk_per_share)
    max_position_value = capital * max_position_pct
    shares_by_cap = math.floor(max_position_value / entry)

    shares = int(max(0, min(shares_by_risk, shares_by_cap)))
    lots_1000 = int(shares // 1000)

    return {"position_value": float(shares * entry), "shares": shares, "lots_1000": lots_1000}
