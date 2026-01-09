import datetime as dt
from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class MarketData:
    stock_meta: pd.DataFrame
    daily_price: pd.DataFrame


def make_demo_market_data(asof: dt.date, num_stocks: int, num_sectors: int, history_days: int, seed: int) -> MarketData:
    rng = np.random.default_rng(seed)

    stock_ids = [f"{1000 + i}" for i in range(num_stocks)]
    sector_ids = [f"S{j:02d}" for j in range(num_sectors)]

    sector = rng.choice(sector_ids, size=num_stocks, replace=True)

    stock_meta = pd.DataFrame(
        {
            "stock_id": stock_ids,
            "stock_name": [f"Stock{sid}" for sid in stock_ids],
            "market": rng.choice(["TWSE", "TPEX"], size=num_stocks, replace=True, p=[0.7, 0.3]),
            "industry": sector,
            "themes": sector,
        }
    )

    dates = pd.date_range(end=pd.Timestamp(asof), periods=history_days, freq="B").date

    base_prices = rng.uniform(18, 220, size=num_stocks)
    base_turnover = rng.uniform(1.5e7, 2.5e8, size=num_stocks)

    sector_momentum = {s: rng.normal(0.001, 0.02, size=len(dates)) for s in sector_ids}

    rows: list[dict] = []
    for t, d in enumerate(dates):
        for i, sid in enumerate(stock_ids):
            s = sector[i]
            drift = sector_momentum[s][t]
            noise = rng.normal(0, 0.025)
            ret = drift + noise

            if t == 0:
                prev_close = base_prices[i]
            else:
                prev_close = rows[-num_stocks + i]["close"]

            close = max(2.0, prev_close * (1.0 + ret))
            open_ = close * (1.0 + rng.normal(0, 0.01))
            high = max(open_, close) * (1.0 + abs(rng.normal(0, 0.01)))
            low = min(open_, close) * (1.0 - abs(rng.normal(0, 0.01)))

            volume = int(rng.uniform(2000, 80000) * (1.0 + abs(ret) * 10))
            turnover = float(base_turnover[i] * (0.4 + abs(ret) * 8) * rng.uniform(0.7, 1.3))

            pct_change = (close / prev_close - 1.0) * 100 if prev_close else 0.0

            rows.append(
                {
                    "trade_date": d,
                    "stock_id": sid,
                    "open": float(open_),
                    "high": float(high),
                    "low": float(low),
                    "close": float(close),
                    "pct_change": float(pct_change),
                    "volume": int(volume),
                    "turnover": float(turnover),
                    "is_limit_up": False,
                    "is_limit_down": False,
                }
            )

    daily_price = pd.DataFrame(rows)

    return MarketData(stock_meta=stock_meta, daily_price=daily_price)
