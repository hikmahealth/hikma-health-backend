class IBaseAdapter:
    """Interface to be implemented by respective store. This adapter allows storage of
    resources like large files, images or blobs needed by a hikma server"""
    def get(self, name: str):
        raise NotImplementedError()

    def put(self, name: str, object: bytes):
        raise NotImplementedError()
