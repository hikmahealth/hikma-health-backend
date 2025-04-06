class Data:
    def to_dict(self) -> dict:
        raise NotImplementedError()


class DictLoader:
    def __init__(self):
        pass

    def __iter__(self):
        pass


class ChangeData:
    def __init__(self) -> None:
        pass

    def transform(self)
