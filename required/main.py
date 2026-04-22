from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from required.analyze_db import analyze_postgres
from required.generator import generate_events
from required.store_db import save_events_to_postgres
from required.store_file import save_events_to_parquet
from required.visualize import write_analysis_charts

DEFAULT_POSTGRES_DSN = "postgresql://postgres:postgres@localhost:5432/events"
DEFAULT_PARQUET_PATH = Path("generated/logs/events.parquet")
DEFAULT_CHARTS_DIR = Path("generated/charts")


def get_postgres_dsn() -> str:
    return os.getenv("POSTGRES_DSN", DEFAULT_POSTGRES_DSN)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate events and store them.")
    parser.add_argument(
        "--backend",
        choices=("db", "file"),
        required=True,
        help="Choose db for PostgreSQL or file for Parquet.",
    )
    parser.add_argument("--count", type=int, default=10, help="Number of events to generate.")
    parser.add_argument("--seed", type=int, default=1, help="Random seed for reproducible events.")
    parser.add_argument(
        "--truncate",
        action="store_true",
        help="Delete existing rows before insert when --backend db is used.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    events = generate_events(count=args.count, seed=args.seed)

    if args.backend == "db":
        dsn = get_postgres_dsn()
        inserted_count = save_events_to_postgres(
            events,
            dsn=dsn,
            truncate=args.truncate,
        )
        print(f"Inserted {inserted_count} events into PostgreSQL.")
        results = analyze_postgres(dsn=dsn)
        chart_paths = write_analysis_charts(results, output_dir=DEFAULT_CHARTS_DIR / "db")
        print(_render_chart_paths(chart_paths))
        return 0

    elif args.backend == "file":
        from required.analyze_file import analyze_parquet

        written_count = save_events_to_parquet(
            events,
            parquet_path=DEFAULT_PARQUET_PATH,
        )
        print(f"Wrote {written_count} events to Parquet: {DEFAULT_PARQUET_PATH}")
        results = analyze_parquet(parquet_path=DEFAULT_PARQUET_PATH)
        chart_paths = write_analysis_charts(results, output_dir=DEFAULT_CHARTS_DIR / "file")
        print(_render_chart_paths(chart_paths))
        return 0

    raise Exception(f"Unknown backend: {args.backend}")


def _render_chart_paths(chart_paths: list[Path]) -> str:
    joined_paths = "\n".join(f"- {path}" for path in chart_paths)
    return f"Generated chart files:\n{joined_paths}"


if __name__ == "__main__":
    raise SystemExit(main())
