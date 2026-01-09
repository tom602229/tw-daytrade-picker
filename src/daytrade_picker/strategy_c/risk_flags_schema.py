import pandas as pd


def empty_risk_flags() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "stock_id",
            "is_disposed",
            "is_full_margin",
            "liquidity_score",
            "is_blacklist",
        ]
    )
