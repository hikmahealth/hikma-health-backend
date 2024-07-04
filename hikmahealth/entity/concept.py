from __future__ import annotations

from hikmahealth.entity import sync

class Patient(sync.SyncronizableEntity):
    TABLE_NAME = "patients"


class Event(sync.SyncronizableEntity):
    TABLE_NAME = "events"
    pass

class Clinic(sync.SyncronizableEntity):
    TABLE_NAME = "clinic"
    pass

class Visit(sync.SyncronizableEntity):
    TABLE_NAME = "visits"