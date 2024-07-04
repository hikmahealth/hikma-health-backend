"""datetime related utilities"""

from datetime import datetime, timezone, date
from typing import Optional, Any

def identity(x):
    return x


def parse_client_timestamp(ts: str):
    for fmt in ('%Y-%m-%dT%H:%M:%S.%fZ', '%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%d'):
        try:
            return datetime.strptime(ts, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    raise ValueError('invalid visit date format')        


def from_timestamp(timestamp: int | str):
    date = datetime.utcfromtimestamp(
        int(timestamp) / 1000).strftime("%Y-%m-%d %H:%M:%S")
    return date



def parse_client_date(date_str: str):
    if not date_str:
        return None
    if date_str == 'None':
        return None  
    return date.fromisoformat(date_str)


def parse_client_bool(bool_int: int):
    return bool_int != 0

def parse_server_uuid(s: str):
    if s is None:
        return None
    return s.replace('-', '')


def as_string(s: Optional[Any]):
    if s is None:
         return None
    return str(s)

# function to convert a javascript timestamp into a datetime object at gmt time
def convert_timestamp_to_gmt(timestamp: int | str):
    # convert the lastPuledAt milliseconds string into a date object of gmt time
    return datetime.fromtimestamp(int(timestamp) / 1000, tz=timezone.utc)


# function to convert a javascript timestamp into a datetime object at gmt time
def convert_timestamp_to_iso(isoTimestamp: str):
    # convert the lastPuledAt milliseconds string into a date object of gmt time
    return datetime.fromisoformat(isoTimestamp).isoformat()

