from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

from required.event import Event, EventType, HttpMethod

PATHS = (
    ("/", HttpMethod.GET, (200, 500)),
    ("/products", HttpMethod.GET, (200, 500)),
    ("/products/1", HttpMethod.GET, (200, 500)),
    ("/products/2", HttpMethod.GET, (200, 500)),
    ("/products/3", HttpMethod.GET, (404, 500)),
    ("/orders", HttpMethod.POST, (201, 400, 500)),
)

KST = timezone(timedelta(hours=9))


def _generate_event(
        seed: int | None = None,
        rng: random.Random | None = None,
) -> Event:
    random_source = rng or random.Random(seed)
    date = _generate_date(random_source)
    user_id = random_source.randint(1, 100)
    session_id = random_source.randint(1000, 9999)
    path, http_method, allowed_status_codes = random_source.choice(PATHS)
    status_code = random_source.choice(allowed_status_codes)

    if 500 <= status_code:
        event_type = EventType.SYSTEM_ERROR
    elif 400 <= status_code:
        event_type = EventType.CLIENT_ERROR
    elif http_method == "POST" and path == "/orders":
        event_type = EventType.PURCHASE
    else:
        event_type = EventType.PAGE_VIEW

    return Event(
        date=date,
        event_type=event_type,
        user_id=user_id,
        session_id=session_id,
        status_code=status_code,
        http_method=http_method,
        path=path,
    )


def _generate_date(rng: random.Random) -> datetime:
    base_time = datetime.now(tz=KST).replace(second=0, microsecond=0)
    return base_time - timedelta(
        hours=rng.randint(0, 71),
        minutes=rng.randint(0, 59),
    )


def generate_events(count: int, seed: int | None = None) -> list[Event]:
    if count <= 0:
        raise ValueError("count must be greater than 0")

    random_source = random.Random(seed)
    return [_generate_event(rng=random_source) for _ in range(count)]


if __name__ == "__main__":
    print(generate_events(10, 1))
