from datetime import datetime
from zoneinfo import ZoneInfo


_JST = ZoneInfo("Asia/Tokyo")


def now_jst() -> datetime:
    return datetime.now(tz=_JST).replace(microsecond=0)


def iso_jst(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=_JST)
    return dt.astimezone(_JST).replace(microsecond=0).isoformat()


def date_jst(dt: datetime):
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=_JST)
    return dt.astimezone(_JST).date()


def parse_iso(s: str) -> datetime:
    return datetime.fromisoformat(s)
