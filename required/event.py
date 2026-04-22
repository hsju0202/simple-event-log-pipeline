from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class HttpMethod(StrEnum):
    GET = "GET"
    POST = "POST"


class EventType(StrEnum):
    PAGE_VIEW = "page_view"
    PURCHASE = "purchase"
    CLIENT_ERROR = "client_error"
    SYSTEM_ERROR = "system_error"


@dataclass(frozen=True)
class Event:
    date: datetime
    event_type: EventType
    user_id: int
    session_id: int
    status_code: int
    http_method: HttpMethod
    path: str

    def to_row(self) -> tuple[object, ...]:
        return (
            self.date,
            self.event_type.value,
            self.user_id,
            self.session_id,
            self.status_code,
            self.http_method.value,
            self.path,
        )
