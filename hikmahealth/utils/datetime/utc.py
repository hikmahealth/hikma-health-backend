from datetime import timezone, datetime, UTC
from dateutil import parser


def now():
    return datetime.now(tz=UTC)


def from_unixtimestamp(unixtimestamp: int | str):
    try:
        return datetime.fromtimestamp(int(unixtimestamp) / 1000, tz=UTC)
    except (ValueError, TypeError, OverflowError):
        return datetime.now(timezone.utc)


def from_iso8601(dt_str: str):
    return parser.isoparse(dt_str).astimezone(tz=UTC)


def from_datetime(dt: datetime):
    """Normalizes the datetime input to a UTC datetime."""
    return dt.astimezone(tz=UTC)
