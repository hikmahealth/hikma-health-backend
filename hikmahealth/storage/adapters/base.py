from abc import abstractmethod
from werkzeug.datastructures import FileStorage


class IBaseStore:
    """Interface to be implemented by respective store. This adapter allows storage of
    resources like large files, images or blobs needed by a hikma server"""
    @abstractmethod
    def get(self, name: str) -> FileStorage:
        raise NotImplementedError()

    @abstractmethod
    def put(self, data: FileStorage, destination: str, **opts):
        raise NotImplementedError()
