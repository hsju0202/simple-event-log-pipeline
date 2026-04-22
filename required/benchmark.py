from __future__ import annotations

import argparse
import os
import statistics
import sys
import time
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from required.analyze_db import (
    ERROR_RATE_SQL as DB_ERROR_RATE_SQL,
    EVENT_TYPE_COUNTS_SQL as DB_EVENT_TYPE_COUNTS_SQL,
    HOURLY_EVENT_TREND_SQL as DB_HOURLY_EVENT_TREND_SQL,
    USER_EVENT_COUNTS_SQL as DB_USER_EVENT_COUNTS_SQL,
)
from required.analyze_file import (
    ERROR_RATE_SQL as FILE_ERROR_RATE_SQL,
    EVENT_TYPE_COUNTS_SQL as FILE_EVENT_TYPE_COUNTS_SQL,
    HOURLY_EVENT_TREND_SQL as FILE_HOURLY_EVENT_TREND_SQL,
    USER_EVENT_COUNTS_SQL as FILE_USER_EVENT_COUNTS_SQL,
)
from required.generator import generate_events
from required.main import DEFAULT_PARQUET_PATH, DEFAULT_POSTGRES_DSN
from required.store_db import save_events_to_postgres
from required.store_file import save_events_to_parquet

DEFAULT_COUNT = 10_000
DEFAULT_WARM_RUNS = 5

POSTGRES_QUERIES = {
    "event_type_counts": DB_EVENT_TYPE_COUNTS_SQL,
    "user_event_counts": DB_USER_EVENT_COUNTS_SQL,
    "hourly_event_trend": DB_HOURLY_EVENT_TREND_SQL,
    "error_rate": DB_ERROR_RATE_SQL,
}

PARQUET_QUERIES = {
    "event_type_counts": FILE_EVENT_TYPE_COUNTS_SQL,
    "user_event_counts": FILE_USER_EVENT_COUNTS_SQL,
    "hourly_event_trend": FILE_HOURLY_EVENT_TREND_SQL,
    "error_rate": FILE_ERROR_RATE_SQL,
}

QUERY_LABELS = {
    "event_type_counts": "이벤트 타입별 개수",
    "user_event_counts": "유저별 이벤트 수",
    "hourly_event_trend": "시간대별 이벤트 추이",
    "error_rate": "에러 비율",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Benchmark DB and file backends.")
    parser.add_argument(
        "--backend",
        choices=("db", "file"),
        required=True,
        help="Choose which backend benchmark to run.",
    )
    parser.add_argument("--count", type=int, default=DEFAULT_COUNT, help="Number of events to benchmark.")
    parser.add_argument("--seed", type=int, default=1, help="Random seed for reproducible events.")
    parser.add_argument(
        "--warm-runs",
        type=int,
        default=DEFAULT_WARM_RUNS,
        help="Number of repeated warm query runs per query.",
    )
    parser.add_argument(
        "--postgres-dsn",
        default=get_postgres_dsn(),
        help="PostgreSQL DSN used for DB benchmarking.",
    )
    parser.add_argument(
        "--parquet-path",
        type=Path,
        default=DEFAULT_PARQUET_PATH,
        help="Parquet path used for file benchmarking.",
    )
    return parser


def get_postgres_dsn() -> str:
    return os.getenv("POSTGRES_DSN", DEFAULT_POSTGRES_DSN)


def main() -> int:
    args = build_parser().parse_args()
    results = benchmark_backends(
        backend=args.backend,
        count=args.count,
        seed=args.seed,
        warm_runs=args.warm_runs,
        postgres_dsn=args.postgres_dsn,
        parquet_path=args.parquet_path,
    )
    print(render_benchmark_report(results))
    return 0


def benchmark_backends(
    *,
    backend: str,
    count: int,
    seed: int,
    warm_runs: int,
    postgres_dsn: str,
    parquet_path: Path,
) -> dict[str, object]:
    events = generate_events(count=count, seed=seed)
    results: dict[str, object] = {"meta": {"count": count, "seed": seed, "warm_runs": warm_runs}}

    if backend == "db":
        results["db"] = benchmark_postgres(events=events, dsn=postgres_dsn, warm_runs=warm_runs)
    else:
        results["file"] = benchmark_parquet(events=events, parquet_path=parquet_path, warm_runs=warm_runs)

    return results


def benchmark_postgres(
    *,
    events: list[object],
    dsn: str,
    warm_runs: int,
) -> dict[str, object]:
    event_count, save_ms = _measure_operation_result_ms(
        lambda: save_events_to_postgres(events, dsn=dsn, truncate=True)
    )
    psycopg = _import_psycopg()

    with psycopg.connect(dsn) as connection:
        storage_bytes = _measure_postgres_storage_bytes(connection)

    queries = {
        name: _measure_postgres_query(dsn=dsn, query=query, warm_runs=warm_runs)
        for name, query in POSTGRES_QUERIES.items()
    }
    return {
        "event_count": event_count,
        "save_ms": save_ms,
        "storage_bytes": storage_bytes,
        "queries": queries,
    }


def benchmark_parquet(
    *,
    events: list[object],
    parquet_path: Path,
    warm_runs: int,
) -> dict[str, object]:
    event_count, save_ms = _measure_operation_result_ms(
        lambda: save_events_to_parquet(events, parquet_path=parquet_path)
    )
    storage_bytes = _measure_file_storage_bytes(parquet_path)
    queries = {
        name: _measure_parquet_query(parquet_path=parquet_path, query=query, warm_runs=warm_runs)
        for name, query in PARQUET_QUERIES.items()
    }
    return {
        "event_count": event_count,
        "save_ms": save_ms,
        "storage_bytes": storage_bytes,
        "queries": queries,
    }


def _measure_postgres_storage_bytes(connection) -> int:
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_total_relation_size('events')")
        return int(cursor.fetchone()[0])


def _measure_file_storage_bytes(parquet_path: Path) -> int:
    return parquet_path.stat().st_size


def _measure_postgres_query(*, dsn: str, query: str, warm_runs: int) -> dict[str, object]:
    cold_ms = _measure_ms(lambda: _run_postgres_query_once(dsn=dsn, query=query))
    psycopg = _import_psycopg()
    with psycopg.connect(dsn) as connection:
        warm_runs_ms = [
            _measure_ms(lambda: _run_postgres_query(connection=connection, query=query))
            for _ in range(warm_runs)
        ]
    return _summarize_query_times(cold_ms=cold_ms, warm_runs_ms=warm_runs_ms)


def _measure_parquet_query(*, parquet_path: Path, query: str, warm_runs: int) -> dict[str, object]:
    cold_ms = _measure_ms(lambda: _run_parquet_query_once(parquet_path=parquet_path, query=query))
    duckdb = _import_duckdb()
    connection = duckdb.connect()
    try:
        warm_runs_ms = [
            _measure_ms(lambda: _run_parquet_query(connection=connection, parquet_path=parquet_path, query=query))
            for _ in range(warm_runs)
        ]
    finally:
        connection.close()
    return _summarize_query_times(cold_ms=cold_ms, warm_runs_ms=warm_runs_ms)


def _run_postgres_query_once(*, dsn: str, query: str) -> None:
    psycopg = _import_psycopg()
    with psycopg.connect(dsn) as connection:
        _run_postgres_query(connection=connection, query=query)


def _run_postgres_query(*, connection, query: str) -> None:
    with connection.cursor() as cursor:
        cursor.execute(query)
        cursor.fetchall()


def _run_parquet_query_once(*, parquet_path: Path, query: str) -> None:
    duckdb = _import_duckdb()
    connection = duckdb.connect()
    try:
        _run_parquet_query(connection=connection, parquet_path=parquet_path, query=query)
    finally:
        connection.close()


def _run_parquet_query(*, connection, parquet_path: Path, query: str) -> None:
    cursor = connection.execute(query, (str(parquet_path),))
    cursor.fetchall()


def _measure_ms(operation: Callable[[], None]) -> float:
    start = time.perf_counter()
    operation()
    return round((time.perf_counter() - start) * 1000, 3)


def _measure_operation_result_ms(operation: Callable[[], int]) -> tuple[int, float]:
    start = time.perf_counter()
    result = operation()
    elapsed_ms = round((time.perf_counter() - start) * 1000, 3)
    return result, elapsed_ms


def _summarize_query_times(*, cold_ms: float, warm_runs_ms: list[float]) -> dict[str, object]:
    return {
        "cold_ms": cold_ms,
        "warm_runs_ms": warm_runs_ms,
        "warm_avg_ms": round(statistics.fmean(warm_runs_ms), 3),
        "warm_min_ms": round(min(warm_runs_ms), 3),
    }


def render_benchmark_report(results: dict[str, object]) -> str:
    meta = results["meta"]
    lines = [
        f"벤치마크 결과(이벤트 수: {meta['count']}, 시드: {meta['seed']}, 반복 실행 수: {meta['warm_runs']})",
        "",
    ]

    for backend in ("db", "file"):
        if backend not in results:
            continue
        backend_results = results[backend]
        lines.extend(
            [
                f"""
백엔드: {backend}
  이벤트 수: {backend_results['event_count']}
  저장 시간(ms): {backend_results['save_ms']}
  저장 용량(bytes): {backend_results['storage_bytes']}
                """.strip(),
            ]
        )
        lines.append("")

        for query_name, query_results in backend_results["queries"].items():
            lines.append(
                f"""
[{QUERY_LABELS[query_name]}]
첫 실행: {query_results['cold_ms']}ms
반복 평균: {query_results['warm_avg_ms']}ms
반복 최소: {query_results['warm_min_ms']}ms
                """.strip()
            )
            lines.append("")

    return "\n".join(lines)


def _import_psycopg():
    try:
        import psycopg  # type: ignore
    except ModuleNotFoundError as error:
        raise RuntimeError('psycopg is required. Install it with: pip install "psycopg[binary]"') from error
    return psycopg


def _import_duckdb():
    try:
        import duckdb  # type: ignore
    except ModuleNotFoundError as error:
        raise RuntimeError("duckdb is required. Install it with: pip install duckdb") from error
    return duckdb


if __name__ == "__main__":
    raise SystemExit(main())
