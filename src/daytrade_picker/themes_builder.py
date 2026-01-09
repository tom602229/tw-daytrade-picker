import re
from pathlib import Path

import pandas as pd


def build_themes_mapping(
    input_path: Path | None,
    input_dir: Path | None,
    out_path: Path,
    sheet: str | None = None,
) -> pd.DataFrame:
    if input_path is None:
        if input_dir is None:
            input_dir = Path.home() / "Desktop" / "CMoneyExports"
        input_path = _pick_latest_export(input_dir)

    df = _read_any(input_path, sheet=sheet)

    stock_col = _guess_stock_id_col(df)
    theme_col = _guess_theme_col(df)

    out = df[[stock_col, theme_col]].copy()
    out.columns = ["stock_id", "themes"]

    out["stock_id"] = out["stock_id"].astype(str).str.strip()
    out["stock_id"] = out["stock_id"].str.extract(r"(\d{4,6})", expand=False)
    out = out[out["stock_id"].notna()].copy()

    out["themes"] = out["themes"].astype(str).str.strip()
    out = out[out["themes"].notna() & (out["themes"] != "")].copy()

    out["themes"] = out["themes"].str.replace(r"\s+", "", regex=True)

    out = (
        out.groupby("stock_id", as_index=False)["themes"]
        .apply(lambda s: ";".join(sorted(set([x for x in s.tolist() if x and x != "nan"]))))
        .reset_index(drop=True)
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(out_path, index=False, encoding="utf-8-sig")
    return out


def _pick_latest_export(input_dir: Path) -> Path:
    if not input_dir.exists():
        raise RuntimeError(f"Input directory does not exist: {input_dir}")

    candidates = []
    for ext in ["*.csv", "*.xlsx", "*.xls"]:
        candidates.extend(input_dir.glob(ext))

    if not candidates:
        raise RuntimeError(f"No export files found in: {input_dir}")

    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0]


def _read_any(path: Path, sheet: str | None) -> pd.DataFrame:
    if path.suffix.lower() == ".csv":
        try:
            return pd.read_csv(path, encoding="utf-8-sig")
        except UnicodeDecodeError:
            return pd.read_csv(path, encoding="cp950")

    if path.suffix.lower() in {".xlsx", ".xls"}:
        return pd.read_excel(path, sheet_name=sheet or 0, engine="openpyxl")

    raise RuntimeError(f"Unsupported export file type: {path}")


def _guess_stock_id_col(df: pd.DataFrame) -> str:
    cols = list(df.columns)

    preferred = [
        "股票代碼",
        "代號",
        "商品代碼",
        "證券代號",
        "stock_id",
        "StockID",
        "Symbol",
        "代碼",
    ]
    for p in preferred:
        for c in cols:
            if str(c).strip() == p:
                return c

    for c in cols:
        s = df[c].astype(str)
        hit = s.str.contains(r"\b\d{4}\b", regex=True, na=False).mean()
        if hit >= 0.5:
            return c

    raise RuntimeError(f"Cannot infer stock_id column from: {cols}")


def _guess_theme_col(df: pd.DataFrame) -> str:
    cols = list(df.columns)

    preferred = [
        "題材",
        "概念",
        "概念股",
        "族群",
        "主題",
        "themes",
        "theme",
        "Theme",
    ]
    for p in preferred:
        for c in cols:
            if p in str(c):
                return c

    non_numeric = []
    for c in cols:
        s = df[c].astype(str)
        numeric_ratio = s.str.fullmatch(r"[\d\.,]+", na=False).mean()
        if numeric_ratio < 0.5:
            non_numeric.append(c)

    if non_numeric:
        return non_numeric[0]

    raise RuntimeError(f"Cannot infer themes column from: {cols}")
