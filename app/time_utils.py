from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def ensure_timezone_aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def to_timezone(value: datetime, timezone_name: str | None) -> datetime:
    aware = ensure_timezone_aware(value)
    if not timezone_name:
        return aware
    try:
        return aware.astimezone(ZoneInfo(timezone_name))
    except ZoneInfoNotFoundError:
        return aware
