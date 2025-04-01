class DeltaData(object):
    """Describes the data and how it should be syncronized.

    Used when sycnronizing in either directions"""

    def __init__(
        self,
        created: list[dict] | None = None,
        updated: list[dict] | None = None,
        deleted: list[str] | None = None,
    ):
        self.created = created if created is not None else []
        self.updated = updated if updated is not None else []
        self.deleted = deleted if deleted is not None else []

    def to_dict(self):
        return dict(created=self.created, updated=self.updated, deleted=self.deleted)

    @property
    def is_empty(self):
        return (
            len(self.created) == 0 and len(self.deleted) == 0 and len(self.updated) == 0
        )
