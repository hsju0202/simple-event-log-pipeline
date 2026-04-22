from __future__ import annotations

from typing import Iterable
from required.event import Event


CREATE_EVENTS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS events (
    id BIGSERIAL PRIMARY KEY,
    date TIMESTAMPTZ NOT NULL,
    event_type TEXT NOT NULL,
    user_id INTEGER NOT NULL,
    session_id INTEGER NOT NULL,
    status_code INTEGER NOT NULL,
    http_method VARCHAR(7) NOT NULL,
    path VARCHAR(255) NOT NULL
)
"""

CREATE_EVENTS_USER_ID_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_events_user_id ON events (user_id)
"""


def save_events_to_postgres(
    events: Iterable[Event],
    *,
    dsn: str,
    truncate: bool = False,
) -> int:
    psycopg = _import_psycopg()
    rows = [event.to_row() for event in events]

    with psycopg.connect(dsn) as connection:
        with connection.cursor() as cursor:
            cursor.execute(CREATE_EVENTS_TABLE_SQL)
            cursor.execute(CREATE_EVENTS_USER_ID_INDEX_SQL)
            if truncate:
                cursor.execute("TRUNCATE TABLE events RESTART IDENTITY")
            cursor.executemany(
                """
                INSERT INTO events (
                    date,
                    event_type,
                    user_id,
                    session_id,
                    status_code,
                    http_method,
                    path
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                rows,
            )
        connection.commit()

    return len(rows)


def _import_psycopg():
    try:
        import psycopg  # type: ignore
    except ModuleNotFoundError as error:
        raise RuntimeError('psycopg is required. Install it with: pip install "psycopg[binary]"') from error
    return psycopg
