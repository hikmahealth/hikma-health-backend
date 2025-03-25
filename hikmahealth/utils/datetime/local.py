"""datetime related utilities"""

from datetime import datetime, timezone


# function to convert a javascript timestamp into a datetime object at gmt time
def convert_timestamp_to_iso(isoTimestamp: str):
	# convert the lastPuledAt milliseconds string into a date object of gmt time
	return datetime.fromisoformat(isoTimestamp).isoformat()


def from_unixtimestamp(unixtimestamp: int | str):
	return datetime.fromtimestamp(int(unixtimestamp) / 1000)
