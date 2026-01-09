import argparse
from pathlib import Path

from .themes_builder import build_themes_mapping
from .tej_themes_builder import build_themes_mapping_from_tej


def add_themes_commands(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("build-themes", help="Build themes_mapping.csv from exported CMoney file")
    p.add_argument("--input", required=False, help="Path to export file (.csv/.xlsx)")
    p.add_argument("--input-dir", required=False, help="Directory containing export files; pick latest")
    p.add_argument("--sheet", required=False, help="Excel sheet name (optional)")
    p.add_argument("--out", required=False, default="data/themes_mapping.csv")

    t = sub.add_parser("build-themes-tej", help="Build themes_mapping.csv from TEJ API")
    t.add_argument("--table", required=True, help="TEJ table name, e.g. TWN/XXXX")
    t.add_argument("--stock-col", required=True, help="Stock id column name in TEJ table")
    t.add_argument("--theme-col", required=True, help="Theme/concept column name in TEJ table")
    t.add_argument("--out", required=False, default="data/themes_mapping.csv")
    t.add_argument("--api-key-env", required=False, default="TEJ_API_KEY")


def handle_themes_command(args) -> int:
    if args.cmd == "build-themes":
        input_path = Path(args.input) if args.input else None
        input_dir = Path(args.input_dir) if args.input_dir else None
        out_path = Path(args.out)

        build_themes_mapping(
            input_path=input_path,
            input_dir=input_dir,
            out_path=out_path,
            sheet=args.sheet,
        )
        print(f"Updated themes mapping: {out_path}")
        return 0

    if args.cmd == "build-themes-tej":
        out_path = Path(args.out)
        build_themes_mapping_from_tej(
            out_path=out_path,
            table=str(args.table),
            stock_col=str(args.stock_col),
            theme_col=str(args.theme_col),
            api_key_env=str(args.api_key_env),
        )
        print(f"Updated themes mapping: {out_path}")
        return 0

    return 1
