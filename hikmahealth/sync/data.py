from typing import Callable, Literal


ACTION_CREATE = 'CREATE'
ACTION_UPDATE = 'UPDATE'
ACTION_DELETE = 'DELETE'

type ActionType = Literal['CREATE'] | Literal['UPDATE'] | Literal['DELETE']


class DeltaData[TCreate, TUpdate, TDelete]:
    """Describes the data and how it should be syncronized."""

    def __init__(
        self,
        created: list[TCreate] | None = None,
        updated: list[TUpdate] | None = None,
        deleted: list[TDelete] | None = None,
    ):
        self.created = created if created is not None else []
        self.updated = updated if updated is not None else []
        self.deleted = deleted if deleted is not None else []

    def __iter__(self):
        for d in self.created:
            yield ACTION_CREATE, d

        for d in self.updated:
            yield ACTION_UPDATE, d

        for d in self.deleted:
            yield ACTION_DELETE, d

    def to_dict(self):
        return dict(created=self.created, updated=self.updated, deleted=self.deleted)

    @property
    def size(self):
        return len(self.created) + len(self.updated) + len(self.deleted)

    def add[TCreatedData, TUpdatedData, TDeletedData](
        self,
        created: list[TCreatedData] | None = None,
        updated: list[TUpdatedData] | None = None,
        deleted: list[TDeletedData] | None = None,
    ):
        cr: list[TCreate | TCreatedData] = list(self.created)
        if created is not None:
            for c in created:
                cr.append(c)

        ur: list[TUpdate | TUpdatedData] = list(self.updated)
        if updated is not None:
            for c in updated:
                ur.append(c)

        dr: list[TDelete | TDeletedData] = list(self.deleted)
        if deleted is not None:
            for c in deleted:
                dr.append(c)

        return DeltaData(created=cr, updated=ur, deleted=dr)

    @property
    def is_empty(self):
        return (
            len(self.created) == 0 and len(self.deleted) == 0 and len(self.updated) == 0
        )
