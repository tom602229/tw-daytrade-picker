import datetime as dt
import json
from typing import Any

import pandas as pd
import requests


_TWSE_MI_INDEX = "https://www.twse.com.tw/exchangeReport/MI_INDEX"
_TWSE_T86 = "https://www.twse.com.tw/rwd/zh/fund/T86"
_TPEX_DAILY_QUOTES = "https://www.tpex.org.tw/web/stock/aftertrading/daily_close_quotes/stk_quote_result.php"
_TPEX_3INST = "https://www.tpex.org.tw/web/stock/3insti/daily_trade/3insti_hedge_result.php"


def _yyyymmdd(d: dt.date) -> str:
    return d.strftime("%Y%m%d")


def _roc_yyy_mm_dd(d: dt.date) -> str:
    roc_year = d.year - 1911
    return f"{roc_year}/{d.month:02d}/{d.day:02d}"


def _req_json(url: str, params: dict[str, Any]) -> dict[str, Any]:
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    try:
        return r.json()
    except requests.exceptions.JSONDecodeError:
        text = (r.text or "").strip()
        if not text or text.startswith("<"):
            return {}
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {}


def fetch_daily_prices_all(run_date: dt.date) -> pd.DataFrame:
    twse = _fetch_twse_prices(run_date)
    tpex = _fetch_tpex_prices(run_date)
    df = pd.concat([twse, tpex], ignore_index=True)
    df["date"] = pd.to_datetime(df["date"]).dt.date
    return df


def _fetch_twse_prices(run_date: dt.date) -> pd.DataFrame:
    payload = _req_json(
        _TWSE_MI_INDEX,
        params={"response": "json", "date": _yyyymmdd(run_date), "type": "ALL"},
    )

    # No data (holiday / future date / not yet published)
    if payload.get("tables") is None and payload.get("data") is None:
        return pd.DataFrame(
            columns=[
                "date",
                "market",
                "stock_id",
                "name",
                "open",
                "high",
                "low",
                "close",
                "volume",
                "turnover",
                "sign",
                "change",
                "pct_change",
                "is_limit_up",
                "is_limit_down",
                "is_disposition",
                "is_full_cash_delivery",
            ]
        )

    # TWSE may return either top-level fields/data or nested tables.
    if payload.get("fields") and payload.get("data"):
        raw = pd.DataFrame(payload.get("data", []), columns=payload.get("fields", []))
    else:
        tables = payload.get("tables", []) or []
        target = None
        for t in tables:
            fields = t.get("fields") or []
            if "證券代號" in fields and "收盤價" in fields and "成交股數" in fields:
                target = t
                break

        if not target:
            return pd.DataFrame(
                columns=[
                    "date",
                    "market",
                    "stock_id",
                    "name",
                    "open",
                    "high",
                    "low",
                    "close",
                    "volume",
                    "turnover",
                    "sign",
                    "change",
                    "pct_change",
                    "is_limit_up",
                    "is_limit_down",
                    "is_disposition",
                    "is_full_cash_delivery",
                ]
            )

        fields = target["fields"]
        data = target.get("data", [])
        raw = pd.DataFrame(data, columns=fields)

    keep = {
        "證券代號": "stock_id",
        "證券名稱": "name",
        "開盤價": "open",
        "最高價": "high",
        "最低價": "low",
        "收盤價": "close",
        "成交股數": "volume",
        "成交金額": "turnover",
        "漲跌(+/-)": "sign",
        "漲跌價差": "change",
    }

    raw = raw[list(keep.keys())].rename(columns=keep)
    raw.insert(0, "date", run_date)
    raw.insert(1, "market", "TWSE")

    for col in ["open", "high", "low", "close", "change"]:
        raw[col] = (
            raw[col]
            .astype(str)
            .str.replace(",", "", regex=False)
            .replace({"--": None, "-": None})
        )
        raw[col] = pd.to_numeric(raw[col], errors="coerce")

    for col in ["volume", "turnover"]:
        raw[col] = raw[col].astype(str).str.replace(",", "", regex=False)
        raw[col] = pd.to_numeric(raw[col], errors="coerce")

    raw["pct_change"] = (raw["change"] / (raw["close"] - raw["change"])) * 100
    raw["pct_change"] = raw["pct_change"].replace([pd.NA, pd.NaT], None)

    raw["is_limit_up"] = False
    raw["is_limit_down"] = False
    raw["is_disposition"] = None
    raw["is_full_cash_delivery"] = None

    return raw


def _fetch_tpex_prices(run_date: dt.date) -> pd.DataFrame:
    payload = _req_json(
        _TPEX_DAILY_QUOTES,
        params={"l": "zh-tw", "d": _roc_yyy_mm_dd(run_date), "o": "json"},
    )

    data = payload.get("aaData") or payload.get("data")
    if not data:
        return pd.DataFrame(
            columns=[
                "date",
                "market",
                "stock_id",
                "name",
                "open",
                "high",
                "low",
                "close",
                "change",
                "volume",
                "turnover",
                "pct_change",
                "is_limit_up",
                "is_limit_down",
                "is_disposition",
                "is_full_cash_delivery",
            ]
        )

    # TPEX columns are positional; keep a conservative subset.
    # Common order: 代號, 名稱, 收盤, 漲跌, 開盤, 最高, 最低, 均價, 成交股數, 成交金額, ...
    rows = []
    for row in data:
        if len(row) < 10:
            continue
        stock_id = str(row[0]).strip()
        name = str(row[1]).strip()
        close = row[2]
        change = row[3]
        open_ = row[4]
        high = row[5]
        low = row[6]
        volume = row[8]
        turnover = row[9]
        rows.append(
            {
                "date": run_date,
                "market": "TPEX",
                "stock_id": stock_id,
                "name": name,
                "open": open_,
                "high": high,
                "low": low,
                "close": close,
                "change": change,
                "volume": volume,
                "turnover": turnover,
            }
        )

    df = pd.DataFrame(rows)

    for col in ["open", "high", "low", "close", "change"]:
        df[col] = df[col].astype(str).str.replace(",", "", regex=False).replace({"--": None, "-": None})
        df[col] = pd.to_numeric(df[col], errors="coerce")

    for col in ["volume", "turnover"]:
        df[col] = df[col].astype(str).str.replace(",", "", regex=False)
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["pct_change"] = (df["change"] / (df["close"] - df["change"])) * 100

    df["is_limit_up"] = False
    df["is_limit_down"] = False
    df["is_disposition"] = None
    df["is_full_cash_delivery"] = None

    return df


def fetch_institution_net_all(run_date: dt.date) -> pd.DataFrame:
    twse = _fetch_twse_institution(run_date)
    tpex = _fetch_tpex_institution(run_date)
    df = pd.concat([twse, tpex], ignore_index=True)
    df["date"] = pd.to_datetime(df["date"]).dt.date
    return df


def _fetch_twse_institution(run_date: dt.date) -> pd.DataFrame:
    payload = _req_json(
        _TWSE_T86,
        params={"response": "json", "date": _yyyymmdd(run_date), "selectType": "ALL"},
    )

    fields = payload.get("fields")
    data = payload.get("data")

    if not fields or not data:
        # Some days might return empty (holiday). Return empty DF.
        return pd.DataFrame(columns=["date", "stock_id", "foreign_net", "invest_net"])

    raw = pd.DataFrame(data, columns=fields)

    def _col(name: str) -> str:
        if name in raw.columns:
            return name
        raise RuntimeError(f"TWSE T86 missing column: {name}")

    out = pd.DataFrame(
        {
            "date": run_date,
            "stock_id": raw[_col("證券代號")].astype(str).str.strip(),
            "foreign_net": raw[_col("外陸資買賣超股數(不含外資自營商)")],
            "invest_net": raw[_col("投信買賣超股數")],
        }
    )

    for col in ["foreign_net", "invest_net"]:
        out[col] = out[col].astype(str).str.replace(",", "", regex=False)
        out[col] = pd.to_numeric(out[col], errors="coerce")

    return out


def _fetch_tpex_institution(run_date: dt.date) -> pd.DataFrame:
    payload = _req_json(
        _TPEX_3INST,
        params={"l": "zh-tw", "se": "EW", "t": "D", "d": _roc_yyy_mm_dd(run_date), "o": "json"},
    )

    fields = payload.get("fields")
    data = payload.get("aaData") or payload.get("data")

    if not fields or not data:
        return pd.DataFrame(columns=["date", "stock_id", "foreign_net", "invest_net"])

    raw = pd.DataFrame(data, columns=fields)

    # Common columns: 代號, 名稱, 外資及陸資(不含外資自營商)買賣超股數, 投信買賣超股數, ...
    foreign_col = None
    invest_col = None
    for c in raw.columns:
        if "外資" in c and "買賣超" in c and foreign_col is None:
            foreign_col = c
        if "投信" in c and "買賣超" in c and invest_col is None:
            invest_col = c

    if foreign_col is None or invest_col is None:
        return pd.DataFrame(columns=["date", "stock_id", "foreign_net", "invest_net"])

    out = pd.DataFrame(
        {
            "date": run_date,
            "stock_id": raw[raw.columns[0]].astype(str).str.strip(),
            "foreign_net": raw[foreign_col],
            "invest_net": raw[invest_col],
        }
    )

    for col in ["foreign_net", "invest_net"]:
        out[col] = out[col].astype(str).str.replace(",", "", regex=False)
        out[col] = pd.to_numeric(out[col], errors="coerce")

    return out
