import argparse
import datetime as dt
from pathlib import Path

from .reporting import generate_report


def add_report_commands(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("report", help="Generate a Markdown + PNG report for a given trade date")
    p.add_argument("--date", required=False, help="YYYY-MM-DD, default=today")
    p.add_argument("--market-dir", required=False, default="DayTradePicker_Results")
    p.add_argument("--results-dir", required=False, default="DayTradePicker_Results")
    p.add_argument("--out-dir", required=False, default="reports")


def handle_report_command(args) -> int:
    if args.cmd != "report":
        return 1

    trade_date = dt.datetime.strptime(args.date, "%Y-%m-%d").date() if args.date else dt.date.today()

    md = generate_report(
        trade_date=trade_date,
        market_dir=Path(args.market_dir),
        results_dir=Path(args.results_dir),
        out_dir=Path(args.out_dir),
    )

    print(f"Report written: {md}")
    return 0
