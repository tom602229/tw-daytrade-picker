import argparse
import datetime as dt
from pathlib import Path

from .auto_run import run_auto
from .pipeline import run_pipeline
from .report_cli import add_report_commands, handle_report_command
from .strategy_c.demo import run_demo
from .strategy_c.real_run import run_strategy_c_real
from .themes_cli import add_themes_commands, handle_themes_command


def _parse_date(date_str: str) -> dt.date:
    return dt.datetime.strptime(date_str, "%Y-%m-%d").date()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="daytrade_picker")
    sub = parser.add_subparsers(dest="cmd", required=True)

    run = sub.add_parser("run", help="Run post-market pipeline")
    run.add_argument("--date", required=False, help="YYYY-MM-DD, default=today")
    run.add_argument("--config", required=False, default="config.yaml")

    demo_c = sub.add_parser("demo-strategy-c", help="Run Strategy C demo with synthetic data")
    demo_c.add_argument("--date", required=False, help="YYYY-MM-DD, default=today")
    demo_c.add_argument("--config", required=False, default="config_strategyC.yml")

    auto = sub.add_parser("run-auto", help="Auto-run post-market pipeline for latest available trading date")
    auto.add_argument("--config", required=False, default="config.yaml")
    auto.add_argument("--max-lookback-days", required=False, type=int, default=7)
    auto.add_argument("--retries", required=False, type=int, default=6)
    auto.add_argument("--retry-sleep-seconds", required=False, type=int, default=300)

    run_c = sub.add_parser("run-strategy-c", help="Run Strategy C on real post-market data (sector=themes)")
    run_c.add_argument("--date", required=False, help="YYYY-MM-DD, default=today")
    run_c.add_argument("--config", required=False, default="config_strategyC.yml")
    run_c.add_argument("--market-dir", required=False, default="DayTradePicker_Results")
    run_c.add_argument("--themes-mapping", required=False, default="data/themes_mapping.csv")
    run_c.add_argument("--history-days", required=False, type=int, default=60)
    run_c.add_argument("--out-dir", required=False, default="DayTradePicker_Results")

    add_themes_commands(sub)
    add_report_commands(sub)

    args = parser.parse_args(argv)

    if args.cmd == "run":
        run_date = _parse_date(args.date) if args.date else dt.date.today()
        run_pipeline(run_date=run_date, config_path=Path(args.config))
        return 0

    if args.cmd == "demo-strategy-c":
        run_date = _parse_date(args.date) if args.date else dt.date.today()
        run_demo(trade_date=run_date, config_path=Path(args.config))
        return 0

    if args.cmd == "run-auto":
        picked = run_auto(
            config_path=Path(args.config),
            max_lookback_days=int(args.max_lookback_days),
            retries=int(args.retries),
            retry_sleep_seconds=int(args.retry_sleep_seconds),
        )
        print(f"Auto-run completed for trade_date={picked.isoformat()}")
        return 0

    if args.cmd == "run-strategy-c":
        run_date = _parse_date(args.date) if args.date else dt.date.today()
        run_strategy_c_real(
            trade_date=run_date,
            config_path=Path(args.config),
            market_dir=Path(args.market_dir),
            themes_mapping_path=Path(args.themes_mapping),
            history_days=int(args.history_days),
            out_dir=Path(args.out_dir),
        )
        return 0

    if args.cmd == "build-themes":
        return handle_themes_command(args)

    if args.cmd == "report":
        return handle_report_command(args)

    return 1
