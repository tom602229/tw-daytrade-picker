import datetime as dt
from pathlib import Path

import pandas as pd


def generate_report(
    trade_date: dt.date,
    market_dir: Path,
    results_dir: Path,
    out_dir: Path,
) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)

    market_path = market_dir / f"market_{trade_date.isoformat()}.csv"
    cand_path = results_dir / f"strategyC_candidates_{trade_date.isoformat()}.csv"

    if not market_path.exists():
        raise RuntimeError(f"Missing market file: {market_path}")
    if not cand_path.exists():
        raise RuntimeError(f"Missing Strategy C candidates file: {cand_path}")

    market = pd.read_csv(market_path, encoding="utf-8-sig")
    cand = pd.read_csv(cand_path, encoding="utf-8-sig")

    for c in ["turnover", "pct_change", "close"]:
        if c in market.columns:
            market[c] = pd.to_numeric(market[c], errors="coerce")

    if "score_total" in cand.columns:
        cand["score_total"] = pd.to_numeric(cand["score_total"], errors="coerce")

    img_score = out_dir / f"score_dist_{trade_date.isoformat()}.png"
    img_themes = out_dir / f"themes_top_{trade_date.isoformat()}.png"
    img_scatter = out_dir / f"turnover_scatter_{trade_date.isoformat()}.png"

    _plot_score_distribution(cand, img_score)
    _plot_top_themes(cand, img_themes)
    _plot_turnover_scatter(market, cand, img_scatter)

    md_path = out_dir / f"report_{trade_date.isoformat()}.md"
    md_path.write_text(
        _render_markdown(trade_date, market, cand, img_score, img_themes, img_scatter),
        encoding="utf-8",
    )

    return md_path


def _plot_score_distribution(cand: pd.DataFrame, out_path: Path) -> None:
    import matplotlib.pyplot as plt

    if "score_total" not in cand.columns or len(cand) == 0:
        fig, ax = plt.subplots(figsize=(7, 3))
        ax.text(0.5, 0.5, "No candidates", ha="center", va="center")
        ax.axis("off")
        fig.tight_layout()
        fig.savefig(out_path, dpi=160)
        plt.close(fig)
        return

    s = cand["score_total"].dropna()

    fig, ax = plt.subplots(figsize=(7, 3.5))
    ax.hist(s, bins=30, color="#2563eb", alpha=0.85)
    ax.set_title("Strategy C score_total distribution")
    ax.set_xlabel("score_total")
    ax.set_ylabel("count")
    fig.tight_layout()
    fig.savefig(out_path, dpi=160)
    plt.close(fig)


def _plot_top_themes(cand: pd.DataFrame, out_path: Path) -> None:
    import matplotlib.pyplot as plt

    if "themes" not in cand.columns or len(cand) == 0:
        fig, ax = plt.subplots(figsize=(7, 3))
        ax.text(0.5, 0.5, "No themes", ha="center", va="center")
        ax.axis("off")
        fig.tight_layout()
        fig.savefig(out_path, dpi=160)
        plt.close(fig)
        return

    tmp = cand.copy()
    if "score_total" in tmp.columns:
        tmp["score_total"] = pd.to_numeric(tmp["score_total"], errors="coerce")

    agg = (
        tmp.groupby("themes", as_index=False)
        .agg(num_candidates=("stock_id", "count"), avg_score=("score_total", "mean"))
        .sort_values(["num_candidates", "avg_score"], ascending=[False, False])
        .head(12)
    )

    fig, ax = plt.subplots(figsize=(8.5, 4.5))
    ax.barh(agg["themes"].astype(str), agg["num_candidates"], color="#16a34a", alpha=0.85)
    ax.invert_yaxis()
    ax.set_title("Top themes by candidate count")
    ax.set_xlabel("# candidates")
    fig.tight_layout()
    fig.savefig(out_path, dpi=160)
    plt.close(fig)


def _plot_turnover_scatter(market: pd.DataFrame, cand: pd.DataFrame, out_path: Path) -> None:
    import matplotlib.pyplot as plt

    if not all(c in market.columns for c in ["turnover", "pct_change"]):
        fig, ax = plt.subplots(figsize=(7, 3))
        ax.text(0.5, 0.5, "Missing turnover/pct_change", ha="center", va="center")
        ax.axis("off")
        fig.tight_layout()
        fig.savefig(out_path, dpi=160)
        plt.close(fig)
        return

    fig, ax = plt.subplots(figsize=(7, 4))
    base = market.dropna(subset=["turnover", "pct_change"]).copy()
    ax.scatter(base["turnover"] / 1e8, base["pct_change"], s=8, alpha=0.25, color="#64748b", label="All")

    if "stock_id" in cand.columns and len(cand) > 0:
        picked_ids = set(cand["stock_id"].astype(str).head(50).tolist())
        sel = base[base["stock_id"].astype(str).isin(picked_ids)]
        ax.scatter(sel["turnover"] / 1e8, sel["pct_change"], s=20, alpha=0.9, color="#ef4444", label="Top candidates")

    ax.set_title("Turnover vs pct_change")
    ax.set_xlabel("turnover (100M TWD)")
    ax.set_ylabel("pct_change (%)")
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(out_path, dpi=160)
    plt.close(fig)


def _render_markdown(
    trade_date: dt.date,
    market: pd.DataFrame,
    cand: pd.DataFrame,
    img_score: Path,
    img_themes: Path,
    img_scatter: Path,
) -> str:
    n_market = len(market)
    n_cand = len(cand)

    top10 = cand.copy()
    for c in ["score_total", "suggest_entry", "suggest_stop"]:
        if c in top10.columns:
            top10[c] = pd.to_numeric(top10[c], errors="coerce")

    show_cols = [c for c in ["stock_id", "stock_name", "themes", "score_total", "suggest_entry", "suggest_stop", "shares"] if c in top10.columns]
    top10_md = "(no candidates)"
    if len(top10) > 0 and show_cols:
        top10_md = _to_markdown_table(top10[show_cols].head(10))

    rel_score = img_score.name
    rel_themes = img_themes.name
    rel_scatter = img_scatter.name

    return "\n".join(
        [
            f"# Strategy C Report ({trade_date.isoformat()})",
            "",
            "## Summary",
            f"- Market rows: `{n_market}`",
            f"- Strategy C candidates: `{n_cand}`",
            "",
            "## Top 10 candidates",
            "",
            top10_md,
            "",
            "## Charts",
            "",
            f"### score_total distribution\n\n![]({rel_score})",
            "",
            f"### Top themes\n\n![]({rel_themes})",
            "",
            f"### Turnover vs pct_change\n\n![]({rel_scatter})",
            "",
            "## Notes",
            "- If you see many `UNKNOWN` themes, expand `data/themes_mapping.csv` or use a paid data source.",
            "- If `suggest_stop` is empty, you likely don't have enough historical market_*.csv files yet.",
        ]
    )


def _to_markdown_table(df: pd.DataFrame) -> str:
    if df is None or len(df) == 0:
        return "(empty)"

    cols = [str(c) for c in df.columns]
    header = "| " + " | ".join(cols) + " |"
    sep = "| " + " | ".join(["---"] * len(cols)) + " |"

    rows = []
    for _, r in df.iterrows():
        cells = []
        for c in cols:
            v = r[c]
            if pd.isna(v):
                s = ""
            else:
                s = str(v)
            s = s.replace("\n", " ")
            cells.append(s)
        rows.append("| " + " | ".join(cells) + " |")

    return "\n".join([header, sep] + rows)
