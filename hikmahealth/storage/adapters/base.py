import dataclasses
from abc import abstractmethod
from io import BytesIO

from hikmahealth.storage.objects import PutOutput


class BaseConfig:
    @property
    @abstractmethod
    def secret_fields(self):
        """List of field that contain information that shouldn't be exposed"""
        raise NotImplementedError()

    def to_dict(
        self,
        ignore_nil: bool = False,
        expose_secret: bool = False,
        mask_placeholder: str = '***',
    ) -> dict[str, str]:
        assert dataclasses.is_dataclass(self), 'base config must be a dataclass'
        fields_ = set([f.name for f in dataclasses.fields(self)])

        # values
        entries = {fn: getattr(self, fn) for fn in fields_}

        if not expose_secret:
            secrets_keys = None

            try:
                secrets_keys = tuple(self.secret_fields)
            except NotImplementedError:
                secrets_keys = tuple()

            for key in entries.keys():
                if key in secrets_keys:
                    entries[key] = mask_placeholder

        if not ignore_nil:
            return entries
        else:
            out = dict()
            for field_name, key in entries.items():
                val = getattr(self, field_name)

                # prevents from outputting 'None' values
                if val is not None:
                    out[field_name] = entries.get(field_name)

            return out


class BaseAdapter:
    """Interface to be implemented by respective store. This adapter allows storage of
    resources like large files, images or blobs needed by a hikma server"""

    def __init__(self, name: str, version: str):
        assert name is not None and name != '', (
            'name to identify the store must be included'
        )

        assert version is not None and version != '', (
            'version of the store must be included'
        )

        self.NAME = name
        self.VERSION = version

    @abstractmethod
    def download_as_bytes(self, name: str, *args, **kwargs) -> BytesIO:
        raise NotImplementedError()

    @abstractmethod
    def put(self, data: BytesIO, destination: str, *args, **kwargs) -> PutOutput:
        raise NotImplementedError()
