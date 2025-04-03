from abc import abstractmethod
from io import BytesIO
from werkzeug.datastructures import FileStorage

from hikmahealth.storage.objects import PutOutput


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
    def download_as_bytes(self, name: str) -> BytesIO:
        raise NotImplementedError()

    @abstractmethod
    def put(self, data: BytesIO, destination: str, **opts) -> PutOutput:
        raise NotImplementedError()
