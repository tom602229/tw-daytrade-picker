import os
from pathlib import Path

import pandas as pd


def build_themes_mapping_from_tej(
    out_path: Path,
    table: str,
    stock_col: str,
    theme_col: str,
    api_key_env: str = "TEJ_API_KEY",
    where: dict | None = None,
    paginate: bool = True,
) -> pd.DataFrame:
    api_key = os.getenv(api_key_env)
    if not api_key:
        raise RuntimeError(f"Missing TEJ api key. Please set environment variable: {api_key_env}")

    try:
        import tejapi  # type: ignore
    except Exception as e:  # pragma: no cover
        raise RuntimeError("Missing dependency 'tejapi'. Install it via: python -m pip install tejapi") from e

    tejapi.ApiConfig.api_key = api_key

    opts = {"columns": [stock_col, theme_col]}

    data = tejapi.get(table, paginate=paginate, opts=opts, **(where or {}))
    df = pd.DataFrame(data)

    if stock_col not in df.columns or theme_col not in df.columns:
        raise RuntimeError(f"TEJ response missing columns. Got={list(df.columns)}")

    out = df[[stock_col, theme_col]].copy()
    out.columns = ["stock_id", "themes"]

    out["stock_id"] = out["stock_id"].astype(str).str.strip()
    out["themes"] = out["themes"].astype(str).str.strip()

    out = out[out["stock_id"].notna() & (out["stock_id"] != "")]
    out = out[out["themes"].notna() & (out["themes"] != "")]

    out = (
        out.groupby("stock_id", as_index=False)["themes"]
        .apply(lambda s: ";".join(sorted(set([x for x in s.tolist() if x and x != "nan"]))))
        .reset_index(drop=True)
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(out_path, index=False, encoding="utf-8-sig")

    return out
