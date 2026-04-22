from __future__ import annotations

EVENT_TYPE_COUNTS_SQL = """
SELECT event_type, COUNT(*) AS event_count
FROM events
GROUP BY event_type
ORDER BY event_count DESC, event_type ASC
"""

USER_EVENT_COUNTS_SQL = """
SELECT user_id, COUNT(*) AS event_count
FROM events
GROUP BY user_id
ORDER BY event_count DESC, user_id ASC
"""

HOURLY_EVENT_TREND_SQL = """
SELECT date_trunc('hour', date) AS hour, COUNT(*) AS event_count
FROM events
GROUP BY hour
ORDER BY hour ASC
"""

ERROR_RATE_SQL = """
SELECT
    COUNT(*) AS total_events,
    COUNT(*) FILTER (WHERE event_type IN ('client_error', 'system_error')) AS error_events,
    ROUND(
        COUNT(*) FILTER (WHERE event_type IN ('client_error', 'system_error'))::numeric
        / NULLIF(COUNT(*), 0) * 100,
        2
    ) AS error_rate_percent
FROM events
"""


def analyze_postgres(*, dsn: str) -> dict[str, list[dict[str, object]]]:
    psycopg = _import_psycopg()
    with psycopg.connect(dsn) as connection:
        return {
            "event_type_counts": _fetch_all(connection, EVENT_TYPE_COUNTS_SQL),
            "user_event_counts": _fetch_all(connection, USER_EVENT_COUNTS_SQL),
            "hourly_event_trend": _fetch_all(connection, HOURLY_EVENT_TREND_SQL),
            "error_rate": _fetch_all(connection, ERROR_RATE_SQL),
        }


def _fetch_all(connection, query: str) -> list[dict[str, object]]:
    with connection.cursor() as cursor:
        cursor.execute(query)
        columns = [description.name for description in cursor.description]
        rows = cursor.fetchall()
    return [dict(zip(columns, row, strict=True)) for row in rows]


def _import_psycopg():
    try:
        import psycopg  # type: ignore
    except ModuleNotFoundError as error:
        raise RuntimeError('psycopg is required. Install it with: pip install "psycopg[binary]"') from error
    return psycopg
