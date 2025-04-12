from hikmahealth.sync.data import DeltaData


def test_deltadata_works():
    dataloader = DeltaData(created=[1, 2], updated=[0])

    assert dataloader.size == 3

    dataloader = dataloader.add(created=[3, 4]).add(updated=[2]).add(deleted=[9])

    assert dataloader.created == [1, 2, 3, 4], "created - don't match"
    assert dataloader.updated == [0, 2], "updated - don't match"
    assert dataloader.deleted == [9], "deleted - don't match"

    assert set(dataloader) == set([
        ('CREATE', 1),
        ('CREATE', 2),
        ('CREATE', 3),
        ('CREATE', 4),
        ('UPDATE', 0),
        ('UPDATE', 2),
        ('DELETE', 9),
    ]), 'the expected transformations are not the same'

    assert dataloader.to_dict() == dict(
        created=[1, 2, 3, 4], updated=[0, 2], deleted=[9]
    ), '.to_dict() not returning the expected results'

    assert not dataloader.is_empty, 'this is not empty'


def test_deltadata_is_empty():
    dataloader = DeltaData()

    assert dataloader.size == 0, 'size == 0'
    assert dataloader.is_empty, 'this is empty'
