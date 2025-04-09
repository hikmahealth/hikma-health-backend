"""
These fields types are intended to work with hikmahealth.entities.core{Entity + dataentity}. These fields
are descriptor implementation created to provide utility when converting between types

Reads:
- Dataclass + Descriptor fields -> https://docs.python.org/3/library/dataclasses.html#descriptor-typed-fields
- Descriptors -> https://docs.python.org/3/howto/descriptor.html
"""

from datetime import datetime, timezone
import json
from typing import Callable, Any
from operator import xor


class _BLANK:
    """Singleton implementation for the help deal with the `BLANK` constant"""

    _instance = None

    @classmethod
    def create(cls):
        if _BLANK._instance is None:
            _BLANK._instance = cls()

        return _BLANK._instance

    def __repr__(self) -> str:
        return '__BLANK__'


BLANK = _BLANK.create()
"""This object represnts a missing value. Since `None` can also be a value, we need a
way to demostrate 'nothing'. Similar to `dataclasses.MISSING`"""


class UTCDateTime:
    """Field to represent a date object that's converted from and ISO8601 string"""

    def __init__(self, default_factory: Callable[[], datetime] | BLANK = BLANK):
        self._default_factory = default_factory

    def __set_name__(self, _, name):
        self._private_name = '__' + name

    def default_value(self):
        if self._default_factory is not BLANK:
            return self._default_factory()

        # TODO: might want to require dev
        # to specify the default_factory
        return datetime.now(tz=timezone.utc)

    def __get__(self, obj, _):
        value = getattr(obj, self._private_name, BLANK)
        if value is BLANK:
            return self.default_value()

        return value

    def __set__(self, obj, value: str | datetime | None):
        value_to_set = None

        if isinstance(value, datetime):
            value_to_set = value
        else:
            # assumes is string
            try:
                if value is None:
                    value_to_set = self.default_value()
                else:
                    value_to_set = datetime.fromisoformat(value)
            except ValueError:
                raise ValueError('input must be datetime or iso-8601 valid string')
            except TypeError:
                raise ValueError(
                    'input must be datetime or iso-8601 valid string. instead got {}'.format(
                        type(value)
                    )
                )

        setattr(obj, self._private_name, value_to_set.astimezone(timezone.utc))


class JSON:
    """Field to represent converting JSON string into friendlier objects like `dict` or `list`"""

    def __init__(
        self,
        default_factory: Callable[[], Any] | _BLANK = BLANK,
        default: Any | _BLANK = BLANK,
    ):
        assert xor(default is BLANK, default_factory is BLANK), (
            'either default or default_factory must be defined'
        )

        self._default_value = default
        self._default_factory = default_factory

    def pull_default(self):
        if self._default_factory is not BLANK:
            return self._default_factory()

        return self._default_value

    def __set_name__(self, _, name):
        self._private_name = '__' + name

    def __get__(self, obj, _):
        output = getattr(obj, self._private_name, BLANK)
        if output is BLANK:
            return self.pull_default()

        # If already a dict or list, return as-is
        if isinstance(output, (dict, list)):
            return output

        # Otherwise parse the string/bytes as JSON
        return json.loads(output)

    def __set__(self, obj, value: str | bytes):
        setattr(obj, self._private_name, value)
