from datetime import timezone, datetime, UTC

def now():
    return datetime.now(tz=UTC)

def from_unixtimestamp(unixtimestamp: int | str):
    return datetime.fromtimestamp(int(unixtimestamp) / 1000, tz=UTC)