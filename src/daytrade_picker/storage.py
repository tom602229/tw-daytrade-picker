import datetime as dt
from pathlib import Path

import pandas as pd


def persist_daily(df: pd.DataFrame, run_date: dt.date, cfg: dict) -> None:
    out_dir = Path(cfg["storage"]["out_dir"]).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)

    csv_path = out_dir / f"market_{run_date.isoformat()}.csv"
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")

    if not cfg["storage"].get("use_sqlite"):
        return

    import sqlite3

    sqlite_path = Path(cfg["storage"]["sqlite_path"]).expanduser()
    sqlite_path.parent.mkdir(parents=True, exist_ok=True)

    table = f"market_{run_date.strftime('%Y%m%d')}"

    with sqlite3.connect(sqlite_path) as conn:
        df.to_sql(table, conn, if_exists="replace", index=False)
