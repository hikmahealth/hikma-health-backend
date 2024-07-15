from datetime import datetime
import json

class _WithSetPrivateName:
    def __set_name__(self, _, name):
        self._private_name = "_" + name     

class FromISOStringDateTime(_WithSetPrivateName):  
    def __get__(self, obj, _=None):
        value = getattr(obj, self._private_name, None)
        return datetime.fromisoformat(value)

    def __set__(self, obj, value: str):
        setattr(obj, self._private_name, value)


class JSON(_WithSetPrivateName):
    def __get__(self, obj, _=None):
        output = getattr(obj, self._private_name, None)
        return json.loads(output)

    def __set__(self, obj, value: str | bytes):
        setattr(obj, self._private_name, value)