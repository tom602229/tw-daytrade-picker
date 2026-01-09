import pandas as pd


def zscore(s: pd.Series) -> pd.Series:
    m = s.mean(skipna=True)
    sd = s.std(skipna=True)
    if pd.isna(sd) or sd == 0:
        return pd.Series([0.0] * len(s), index=s.index)
    return (s - m) / sd


def compute_daily_features(daily_price: pd.DataFrame) -> pd.DataFrame:
    df = daily_price.copy()
    df = df.sort_values(["stock_id", "trade_date"]).reset_index(drop=True)

    g = df.groupby("stock_id", sort=False)

    for w in [5, 10, 20]:
        df[f"ma_{w}"] = g["close"].transform(lambda x: x.rolling(w, min_periods=w).mean())

    df["vol_20d_avg"] = g["volume"].transform(lambda x: x.rolling(20, min_periods=20).mean())
    df["vol_ratio_20d"] = df["volume"] / df["vol_20d_avg"]

    df["high_20d"] = g["high"].transform(lambda x: x.rolling(20, min_periods=20).max())
    df["is_20d_high"] = df["close"] >= df["high_20d"]
    df["distance_to_20d_high"] = (df["high_20d"] - df["close"]) / df["high_20d"]

    rng = (df["high"] - df["low"]).replace(0, pd.NA)
    df["pos_in_day"] = (df["close"] - df["low"]) / rng

    return df[
        [
            "trade_date",
            "stock_id",
            "ma_5",
            "ma_10",
            "ma_20",
            "vol_20d_avg",
            "vol_ratio_20d",
            "is_20d_high",
            "distance_to_20d_high",
            "pos_in_day",
        ]
    ]


def compute_sector_daily(stock_meta: pd.DataFrame, daily_price: pd.DataFrame, sector_col: str, mtm_lookback: int) -> pd.DataFrame:
    base = daily_price.merge(stock_meta[["stock_id", sector_col]], on="stock_id", how="left")

    grp = base.groupby(["trade_date", sector_col], as_index=False)
    sector = grp.agg(
        avg_pct_change=("pct_change", "mean"),
        median_pct_change=("pct_change", "median"),
        up_ratio=("pct_change", lambda x: (x > 0).mean()),
        num_up_3=("pct_change", lambda x: (x >= 3).sum()),
    )

    sector = sector.sort_values([sector_col, "trade_date"]).reset_index(drop=True)
    g = sector.groupby(sector_col, sort=False)

    sector["sector_mtm_5d"] = g["avg_pct_change"].transform(lambda x: x.rolling(mtm_lookback, min_periods=mtm_lookback).mean())
    sector["sector_mtm_z"] = g["sector_mtm_5d"].transform(zscore)

    return sector.rename(columns={sector_col: "sector_id"})
