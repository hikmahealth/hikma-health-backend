from __future__ import annotations

from hikmahealth.entity import sync

class Entity(object):
    @classmethod
    @property
    def TABLE_NAME(self) -> str:
        """This refers to the name of the able associated with
        the entity"""
        raise NotImplementedError(f"require {__class__}.TABLE_NAME to be defined")
    


