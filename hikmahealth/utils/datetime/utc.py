from datetime import timezone, datetime, UTC
import dateutil

def now():
    return datetime.now(tz=UTC)

def from_unixtimestamp(unixtimestamp: int | str):
    return datetime.fromtimestamp(int(unixtimestamp) / 1000, tz=UTC)

def from_iso8601(dt_str: str):
    return dateutil.parser.isoparse(dt_str).astimezone(tz=UTC)

def from_datetime(dt: datetime):
    """Normalizes the datetime input to a UTC datetime."""
    return dt.astimezone(tz=UTC)