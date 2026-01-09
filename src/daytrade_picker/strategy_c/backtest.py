from __future__ import annotations

import datetime as dt

import pandas as pd

from .strategy import run_strategy_c


def backtest_strategy_c(
    start_date: dt.date,
    end_date: dt.date,
    capital: float,
    risk_per_trade: float,
    stock_meta: pd.DataFrame,
    daily_price: pd.DataFrame,
    cfg: dict,
    max_positions: int = 5,
    hold_days: int = 2,
) -> pd.DataFrame:
    dates = sorted([d for d in set(daily_price["trade_date"].tolist()) if start_date <= d <= end_date])

    equity = capital
    curve = []

    for i, d in enumerate(dates):
        if i + 1 >= len(dates):
            break

        next_d = dates[i + 1]

        bt_cfg = dict(cfg)
        bt_cfg["position_sizing"] = dict(bt_cfg.get("position_sizing", {}))
        bt_cfg["position_sizing"]["capital"] = equity
        bt_cfg["position_sizing"]["risk_per_trade"] = risk_per_trade

        candidates, _, _, _ = run_strategy_c(
            trade_date=d,
            stock_meta=stock_meta,
            daily_price=daily_price[daily_price["trade_date"] <= d].copy(),
            risk_flags=None,
            cfg=bt_cfg,
        )

        picks = candidates.head(max_positions)

        if len(picks) == 0:
            curve.append({"trade_date": next_d, "equity": equity, "num_trades": 0, "pnl": 0.0})
            continue

        pnl_total = 0.0
        trades = 0
        for _, row in picks.iterrows():
            sid = row["stock_id"]

            entry_px = _get_price(daily_price, next_d, sid, "open")
            if entry_px is None:
                continue

            exit_date = dates[min(i + 1 + hold_days, len(dates) - 1)]
            exit_px = _get_price(daily_price, exit_date, sid, "close")
            if exit_px is None:
                continue

            shares = int(row.get("shares") or 0)
            if shares <= 0:
                continue

            pnl = (exit_px - entry_px) * shares
            pnl_total += pnl
            trades += 1

        equity = equity + pnl_total
        curve.append({"trade_date": next_d, "equity": equity, "num_trades": trades, "pnl": pnl_total})

    return pd.DataFrame(curve)


def _get_price(daily_price: pd.DataFrame, trade_date: dt.date, stock_id: str, col: str) -> float | None:
    r = daily_price[(daily_price["trade_date"] == trade_date) & (daily_price["stock_id"] == stock_id)]
    if len(r) == 0:
        return None
    v = r.iloc[0][col]
    if pd.isna(v):
        return None
    return float(v)
