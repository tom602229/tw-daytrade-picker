from __future__ import annotations

import datetime as dt

import pandas as pd

from .factors import compute_daily_features, compute_sector_daily, zscore
from .risk import apply_universe_filters, size_suggestion, suggest_stop


def run_strategy_c(
    trade_date: dt.date,
    stock_meta: pd.DataFrame,
    daily_price: pd.DataFrame,
    risk_flags: pd.DataFrame | None,
    cfg: dict,
    sector_mode: str = "industry",
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    demo_fallback = bool(cfg.get("demo", {}).get("fallback_if_empty", False))

    features = compute_daily_features(daily_price)
    sector_daily = compute_sector_daily(stock_meta, daily_price, sector_col=sector_mode, mtm_lookback=int(cfg["sector"]["mtm_lookback"]))

    px_d = daily_price[daily_price["trade_date"] == trade_date].copy()
    ft_d = features[features["trade_date"] == trade_date].copy()

    base = px_d.merge(stock_meta, on="stock_id", how="left")
    base = base.merge(ft_d, on=["trade_date", "stock_id"], how="left")

    if risk_flags is not None and len(risk_flags) > 0:
        base = base.merge(risk_flags, on="stock_id", how="left")

    base = apply_universe_filters(base, cfg)

    sec_d = sector_daily[sector_daily["trade_date"] == trade_date].copy()

    sec_d["avg_pct_change_z"] = zscore(sec_d["avg_pct_change"])
    w = cfg["sector"]["weights"]
    sec_d["sector_score"] = (
        float(w["avg_pct_change_z"]) * sec_d["avg_pct_change_z"]
        + float(w["sector_mtm_z"]) * sec_d["sector_mtm_z"].fillna(0)
        + float(w["up_ratio"]) * sec_d["up_ratio"].fillna(0)
    )

    sec_filter = (
        (sec_d["avg_pct_change"] >= float(cfg["sector"]["thresh_avg_pct"]))
        & (sec_d["up_ratio"] >= float(cfg["sector"]["thresh_up_ratio"]))
        & (sec_d["sector_mtm_z"].fillna(0) >= float(cfg["sector"]["thresh_mtm_z"]))
    )

    strong_sectors = sec_d[sec_filter][["sector_id", "sector_score", "avg_pct_change", "up_ratio", "sector_mtm_z"]].copy()

    if len(strong_sectors) == 0 and demo_fallback:
        strong_sectors = (
            sec_d[["sector_id", "sector_score", "avg_pct_change", "up_ratio", "sector_mtm_z"]]
            .sort_values("sector_score", ascending=False)
            .head(3)
            .copy()
        )

    if len(strong_sectors) == 0:
        empty = pd.DataFrame(columns=[
            "trade_date",
            "stock_id",
            "leader_id",
            "sector_id",
            "score_sector",
            "score_leader",
            "score_follow",
            "score_total",
            "suggest_entry",
            "suggest_stop",
            "position_value",
            "shares",
            "lots_1000",
        ])
        return empty, features, sector_daily, strong_sectors

    base = base.rename(columns={sector_mode: "sector_id"})
    base = base[base["sector_id"].isin(strong_sectors["sector_id"])].copy()
    base = base.merge(strong_sectors[["sector_id", "sector_score"]], on="sector_id", how="left")

    base["pct_change_z"] = base.groupby("sector_id")["pct_change"].transform(zscore)
    base["vol_ratio_z"] = base.groupby("sector_id")["vol_ratio_20d"].transform(zscore)

    leader_cfg = cfg["leader"]
    leader_filter = (
        (base["pct_change"].fillna(-999) >= float(leader_cfg["thresh_leader_pct"]))
        & (base["vol_ratio_20d"].fillna(0) >= float(leader_cfg["thresh_leader_vol_ratio"]))
        & (base["is_20d_high"].fillna(False) == True)  # noqa: E712
        & (base["pos_in_day"].fillna(0) >= float(leader_cfg["thresh_leader_pos"]))
    )

    leaders = base[leader_filter].copy()

    if len(leaders) == 0:
        # Fallback: pick leaders by top percentile (or top-N) within sector.
        top_pct = float(leader_cfg.get("top_pct_in_sector", 0.0) or 0.0)
        if top_pct > 0:
            ranked = base.sort_values(["sector_id", "pct_change"], ascending=[True, False]).copy()
            ranked["_rank"] = ranked.groupby("sector_id").cumcount() + 1
            ranked["_n"] = ranked.groupby("sector_id")["stock_id"].transform("count")
            ranked["_cut"] = (ranked["_n"] * top_pct).round().clip(lower=1)
            leaders = ranked[ranked["_rank"] <= ranked["_cut"]].copy()
        elif demo_fallback:
            leaders = base.sort_values(["sector_id", "pct_change"], ascending=[True, False]).copy()

    lw = leader_cfg["weights"]
    leaders["score_leader"] = (
        float(lw["pct_change_z"]) * leaders["pct_change_z"].fillna(0)
        + float(lw["vol_ratio_z"]) * leaders["vol_ratio_z"].fillna(0)
        + float(lw["pos_in_day"]) * leaders["pos_in_day"].fillna(0)
    )

    leaders = (
        leaders.sort_values(["sector_id", "score_leader"], ascending=[True, False])
        .groupby("sector_id", as_index=False, sort=False)
        .head(int(leader_cfg["top_n_per_sector"]))
        .reset_index(drop=True)
    )

    followers_cfg = cfg["follower"]

    followers_filter = (
        (base["pct_change"].fillna(-999) >= float(followers_cfg["pct_change_min"]))
        & (base["pct_change"].fillna(999) <= float(followers_cfg["pct_change_max"]))
        & (base["vol_ratio_20d"].fillna(0) >= float(followers_cfg["vol_ratio_min"]))
        & (base["vol_ratio_20d"].fillna(0) <= float(followers_cfg["vol_ratio_max"]))
        & (base["close"].fillna(0) > base["ma_5"].fillna(1e18))
        & (base["close"].fillna(0) > base["ma_10"].fillna(1e18))
        & (base["distance_to_20d_high"].fillna(1.0) <= float(followers_cfg["thresh_dist_20d_high"]))
    )

    followers = base[followers_filter].copy()

    if len(followers) == 0 and demo_fallback:
        # Fallback: relax MA & distance constraints in demo so we can see ranking behavior.
        followers = base[
            (base["pct_change"].fillna(-999) >= float(followers_cfg["pct_change_min"]))
            & (base["pct_change"].fillna(999) <= float(followers_cfg["pct_change_max"]))
        ].copy()

    fw = followers_cfg["weights"]
    followers["score_follow"] = (
        float(fw["pct_change_z"]) * followers["pct_change_z"].fillna(0)
        + float(fw["vol_ratio_z"]) * followers["vol_ratio_z"].fillna(0)
        + float(fw["one_minus_dist_20d_high"]) * (1.0 - followers["distance_to_20d_high"].fillna(1.0))
        + float(fw["pos_in_day"]) * followers["pos_in_day"].fillna(0)
    )

    if len(leaders) == 0 or len(followers) == 0:
        empty = pd.DataFrame(columns=[
            "trade_date",
            "stock_id",
            "leader_id",
            "sector_id",
            "score_sector",
            "score_leader",
            "score_follow",
            "score_total",
            "suggest_entry",
            "suggest_stop",
            "position_value",
            "shares",
            "lots_1000",
        ])
        return empty, features, sector_daily, strong_sectors

    leader_pick = leaders[["sector_id", "stock_id", "score_leader"]].rename(columns={"stock_id": "leader_id"})

    followers = followers.merge(leader_pick, on="sector_id", how="left")
    followers = followers[followers["leader_id"].notna()].copy()

    tw = cfg["total_score_weights"]
    followers["score_sector"] = followers["sector_score"].fillna(0)
    followers["score_total"] = (
        float(tw["score_sector"]) * followers["score_sector"]
        + float(tw["score_leader"]) * followers["score_leader"].fillna(0)
        + float(tw["score_follow"]) * followers["score_follow"].fillna(0)
    )

    prev_date = _prev_trade_date(daily_price, trade_date)
    prev_low = None
    if prev_date is not None:
        prev_low = (
            daily_price[daily_price["trade_date"] == prev_date][["stock_id", "low"]]
            .rename(columns={"low": "prev_low"})
            .copy()
        )
        followers = followers.merge(prev_low, on="stock_id", how="left")
    else:
        followers["prev_low"] = pd.NA

    ps = cfg["position_sizing"]
    buffer_pct = float(ps["stop_buffer_pct"])

    followers["suggest_entry"] = followers["close"].astype(float)
    followers["suggest_stop"] = followers["prev_low"].apply(lambda x: suggest_stop(float(x) if pd.notna(x) else None, buffer_pct))

    capital = float(ps["capital"])
    risk_per_trade = float(ps["risk_per_trade"])
    max_position_pct = float(ps["max_position_pct"])

    sizing = followers.apply(
        lambda r: size_suggestion(
            capital=capital,
            risk_per_trade=risk_per_trade,
            entry=float(r["suggest_entry"]) if pd.notna(r["suggest_entry"]) else None,
            stop=float(r["suggest_stop"]) if pd.notna(r["suggest_stop"]) else None,
            max_position_pct=max_position_pct,
        ),
        axis=1,
        result_type="expand",
    )

    followers = pd.concat([followers, sizing], axis=1)

    out = followers[
        [
            "trade_date",
            "stock_id",
            "leader_id",
            "sector_id",
            "score_sector",
            "score_leader",
            "score_follow",
            "score_total",
            "suggest_entry",
            "suggest_stop",
            "position_value",
            "shares",
            "lots_1000",
        ]
    ].copy()

    out = out.sort_values("score_total", ascending=False).reset_index(drop=True)

    return out, features, sector_daily, strong_sectors


def _prev_trade_date(daily_price: pd.DataFrame, d: dt.date) -> dt.date | None:
    dates = sorted(set(daily_price["trade_date"].tolist()))
    if d not in dates:
        return None
    idx = dates.index(d)
    if idx == 0:
        return None
    return dates[idx - 1]
