from __future__ import annotations

from pathlib import Path
from typing import Iterable

from required.event import Event

EVENT_COLUMNS = (
    "date",
    "event_type",
    "user_id",
    "session_id",
    "status_code",
    "http_method",
    "path",
)


def save_events_to_parquet(
    events: Iterable[Event],
    *,
    parquet_path: Path,
) -> int:
    pandas = _import_pandas()
    data_frame = pandas.DataFrame.from_records(
        (event.to_row() for event in events),
        columns=EVENT_COLUMNS,
    )
    parquet_path.parent.mkdir(parents=True, exist_ok=True)
    parquet_path.unlink(missing_ok=True)
    data_frame.to_parquet(parquet_path, index=False, engine="pyarrow")

    return len(data_frame.index)

def _import_pandas():
    try:
        import pandas  # type: ignore
    except ModuleNotFoundError as error:
        raise RuntimeError("pandas is required. Install it with: pip install pandas pyarrow") from error
    return pandas
