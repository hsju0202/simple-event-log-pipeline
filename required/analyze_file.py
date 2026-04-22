from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path


EVENT_TYPE_COUNTS_SQL = """
SELECT event_type, COUNT(*) AS event_count
FROM read_parquet(?)
GROUP BY event_type
ORDER BY event_count DESC, event_type ASC
"""

USER_EVENT_COUNTS_SQL = """
SELECT user_id, COUNT(*) AS event_count
FROM read_parquet(?)
GROUP BY user_id
ORDER BY event_count DESC, user_id ASC
"""

HOURLY_EVENT_TREND_SQL = """
SELECT date_trunc('hour', date) AS hour, COUNT(*) AS event_count
FROM read_parquet(?)
GROUP BY hour
ORDER BY hour ASC
"""

ERROR_RATE_SQL = """
SELECT
    COUNT(*) AS total_events,
    COUNT(*) FILTER (WHERE event_type IN ('client_error', 'system_error')) AS error_events,
    ROUND(
        COUNT(*) FILTER (WHERE event_type IN ('client_error', 'system_error'))::DOUBLE
        / NULLIF(COUNT(*), 0) * 100,
        2
    ) AS error_rate_percent
FROM read_parquet(?)
"""


def analyze_parquet(*, parquet_path: Path) -> dict[str, list[dict[str, object]]]:
    duckdb = _import_duckdb()
    connection = duckdb.connect()
    try:
        return {
            "event_type_counts": _fetch_all(connection, EVENT_TYPE_COUNTS_SQL, (str(parquet_path),)),
            "user_event_counts": _fetch_all(connection, USER_EVENT_COUNTS_SQL, (str(parquet_path),)),
            "hourly_event_trend": _fetch_all(connection, HOURLY_EVENT_TREND_SQL, (str(parquet_path),)),
            "error_rate": _fetch_all(connection, ERROR_RATE_SQL, (str(parquet_path),)),
        }
    finally:
        connection.close()


def _fetch_all(connection, query: str, params: Sequence[object]) -> list[dict[str, object]]:
    cursor = connection.execute(query, params)
    columns = [description[0] for description in cursor.description]
    rows = cursor.fetchall()
    return [dict(zip(columns, row, strict=True)) for row in rows]


def _import_duckdb():
    try:
        import duckdb  # type: ignore
    except ModuleNotFoundError as error:
        raise RuntimeError("duckdb is required. Install it with: pip install duckdb") from error
    return duckdb
