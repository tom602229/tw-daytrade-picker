import datetime as dt
from pathlib import Path

import pandas as pd


def write_daily_outputs(df: pd.DataFrame, run_date: dt.date, cfg: dict) -> None:
    out_dir = Path(cfg["storage"]["out_dir"]).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)

    cols = [
        "stock_id",
        "name",
        "market",
        "close",
        "pct_change",
        "turnover",
        "volume",
        "foreign_net",
        "invest_net",
        "score",
    ]

    out = df.copy()
    for c in cols:
        if c not in out.columns:
            out[c] = pd.NA

    out = out[cols]

    csv_path = out_dir / f"candidates_{run_date.isoformat()}.csv"
    out.to_csv(csv_path, index=False, encoding="utf-8-sig")

    xlsx_path = out_dir / f"{run_date.isoformat()}.xlsx"
    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as w:
        out.to_excel(w, index=False, sheet_name="Candidates")
