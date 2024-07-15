from __future__ import annotations

import dataclasses
        
dataentity = dataclasses.dataclass(init=False, kw_only=True)

class Entity:
    @property
    def fields_(self):
        # 'TABLE_NAME' is a reserved field
        return set([f.name for f in dataclasses.fields(self) if f.name != 'TABLE_NAME'])
    
    def __init__(self, **kwargs):
        names = self.fields_
        for k, v in kwargs.items():
            # 'TABLE_NAME' is a reserved field
            if k == 'TABLE_NAME':
                continue

            if k in names:
                setattr(self, k, v)

    def to_dict(self, ignore_nil: bool = False):
        if not ignore_nil:
            return { fn: getattr(self, fn) for fn in self.fields_ }
        else:
            out = dict()
            for field_name in self.fields_:
                val = getattr(self, field_name)

                # prevents from outputting 'None' values
                if val is not None:
                    out[field_name] = val

            return out     

    @property
    @classmethod
    def TABLE_NAME(self) -> str:
        """This refers to the name of the able associated with
        the entity"""
        raise NotImplementedError(f"require {__class__.__name__}.TABLE_NAME to be defined")
    



