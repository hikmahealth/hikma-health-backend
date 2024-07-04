from __future__ import annotations

from hikmahealth.entity import base

class Patient(base.SyncronizableEntity):
    TABLE_NAME = "patients"

    @classmethod
    def from_id(cls, id: str) -> Patient:
        raise NotImplementedError()


class Event(base.SyncronizableEntity):
    TABLE_NAME = "events"
    pass

class Clinic(base.SyncronizableEntity):
    TABLE_NAME = "clinic"
    pass

class Visit(base.SyncronizableEntity):
    TABLE_NAME = "visits"