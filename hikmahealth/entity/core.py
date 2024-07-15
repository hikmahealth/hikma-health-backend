from __future__ import annotations

import dataclasses
        
dataentity = dataclasses.dataclass(init=False)

# def _initializer(self, **kwargs):
#     names = self.fields_
#     for k, v in kwargs.items():
#         # 'TABLE_NAME' is a reserved field
#         if k == 'TABLE_NAME':
#             continue

#         if k in names:
#             setattr(self, k, v)

# class dataentity:
#     def __init__(self, cls):
#         self._class = dataclasses.make_dataclass(cls, init=False)


#     def __call__(self, *args: dataclasses.Any, **kwds: dataclasses.Any) -> dataclasses.Any:
#         # checks if "TABLE_NAME" is defined
#         getattr(self._class, 'TABLE_NAME')

#         self._class.__init__ = _initializer
#         self._class.fields_ = property(lambda self: set([f.name for f in dataclasses.fields(self) if f.name != 'TABLE_NAME']))
#         return self._class

    
    
# def the_entity(table_name: str | None = None):
#     def _special_init_(self, **kwargs):
#         names = self.fields_
#         for k, v in kwargs.items():
#             if k == 'TABLE_NAME':
#                 # 'TABLE_NAME' is a reserved field
#                 continue

#             if k in names:
#                 setattr(self, k, v)

#     def fields_(self):
#         # 'TABLE_NAME' is a reserved field
#         return set([f.name for f in dataclasses.fields(self) if f.name != 'TABLE_NAME'])
                
#     def decorate_class(cls):
#          cls.__init__ = _special_init_
#          cls.fields_ = fields_
#          dataclasses.dataclass(init=False)(cls)
            
#     return decorate_class

@dataclasses.dataclass(init=False)
class Entity():
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

    @classmethod
    @property
    def TABLE_NAME(self) -> str:
        """This refers to the name of the able associated with
        the entity"""
        raise NotImplementedError(f"require {__class__.__name__}.TABLE_NAME to be defined")
    


