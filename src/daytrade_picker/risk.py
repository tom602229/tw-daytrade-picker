import pandas as pd


def apply_risk_filter(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    r = cfg.get("risk", {})

    out = df.copy()

    min_turnover = r.get("min_turnover")
    if min_turnover is not None:
        out = out[out["turnover"].fillna(0) >= float(min_turnover)]

    min_price = r.get("min_price")
    if min_price is not None:
        out = out[out["close"].fillna(0) >= float(min_price)]

    max_price = r.get("max_price")
    if max_price is not None:
        out = out[out["close"].fillna(0) <= float(max_price)]

    if r.get("exclude_disposition"):
        out = out[out["is_disposition"].fillna(False) == False]  # noqa: E712

    if r.get("exclude_full_cash_delivery"):
        out = out[out["is_full_cash_delivery"].fillna(False) == False]  # noqa: E712

    return out
