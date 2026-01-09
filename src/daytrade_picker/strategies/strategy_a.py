import pandas as pd


def apply_strategy_a(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    s = cfg.get("strategy_A", {})

    out = df.copy()

    # Minimal MVP: Only uses same-day features.
    # vol_ratio/new-high/MA need historical data; kept as NaN for now until history module is added.
    for col in ["vol_ratio", "ma20", "is_20d_high", "close_pos"]:
        if col not in out.columns:
            out[col] = pd.NA

    if "close_pos" in out.columns:
        hl_range = (out["high"] - out["low"]).replace(0, pd.NA)
        out["close_pos"] = (out["close"] - out["low"]) / hl_range

    min_pct = s.get("min_pct_change")
    max_pct = s.get("max_pct_change")
    if min_pct is not None:
        out = out[out["pct_change"].fillna(-999) >= float(min_pct)]
    if max_pct is not None:
        out = out[out["pct_change"].fillna(999) <= float(max_pct)]

    close_pos_min = s.get("close_position_min")
    if close_pos_min is not None:
        out = out[out["close_pos"].fillna(0) >= float(close_pos_min)]

    if s.get("require_institution_net_buy"):
        inst_ok = (out["foreign_net"].fillna(0) > 0) | (out["invest_net"].fillna(0) > 0)
        out = out[inst_ok]

    out = _score(out)
    out = out.sort_values(["score", "turnover"], ascending=[False, False])

    return out


def _score(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    pct = out["pct_change"].fillna(0)
    turnover = out["turnover"].fillna(0)
    foreign = out["foreign_net"].fillna(0)
    invest = out["invest_net"].fillna(0)

    out["score"] = (
        pct.clip(lower=0) * 2
        + (turnover / 1e8).clip(upper=10)
        + (foreign / 1e5).clip(lower=-5, upper=10)
        + (invest / 1e5).clip(lower=-5, upper=10)
    )

    return out
