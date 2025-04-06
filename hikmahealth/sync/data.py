from typing import Callable


class CreateDelta:
    pass


ACTION_CREATE = 'CREATE'
ACTION_UPDATE = 'UPDATE'
ACTION_DELETE = 'DELETE'


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

    # def apply_to_delta(
    #     self,
    #     on_create: Callable | None = None,
    #     on_update: Callable | None = None,
    #     on_delete: Callable | None = None,
    # ):
    #     updated = self.updated
    #     deleted = self.deleted

    #     if on_create is not None:
    #         assert callable(on_create), (
    #             '`on_created` must be callable, otherwise, leave as None'
    #         )

    #         created = on_create(self.created)
    #     else:
    #         created = self.created

    #     return DeltaData(created, updated, deleted)

    def to_dict(self):
        return dict(created=self.created, updated=self.updated, deleted=self.deleted)

    @property
    def is_empty(self):
        return (
            len(self.created) == 0 and len(self.deleted) == 0 and len(self.updated) == 0
        )
