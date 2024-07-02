from abc import abstractmethod

class Client(object):
    pass

class Syncable(object):
    """Inferface to help implement features needed by an entity that 
    wants to syncronize content between the client and server"""
    def __init__(self):
        pass

    @abstractmethod
    def get_delta_records(self): 
        raise NotImplementedError()