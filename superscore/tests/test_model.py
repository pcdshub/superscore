from typing import Any
from uuid import uuid4

import pytest
from apischema import ValidationError

from superscore.model import Root, Value


def test_validate_fields(sample_database: Root):
    sample_database.validate()


# TODO: be comprehensive with these validation failures
@pytest.mark.parametrize(
    'entry_index,replace_fld,replace_obj',
    [
        [0, 'pv_name', 1],
        [2, 'parameters', [1, 2, 3, 4]]
    ]
)
def test_validate_failure(
    sample_database: Root,
    entry_index: int,
    replace_fld: str,
    replace_obj: Any
):
    entry = sample_database.entries[entry_index]
    sample_database.validate()
    setattr(entry, replace_fld, replace_obj)

    with pytest.raises(ValidationError):
        sample_database.validate()
    with pytest.raises(ValidationError):
        entry.validate()


@pytest.mark.parametrize(
    'data,valid',
    [
        [1, True], ['one', True], [True, True], [1.1, True],
        [object(), False]
    ]
)
def test_epics_type_validate(data: Any, valid: bool):
    value = Value(
        name='My Value',
        description='description value',
        data=data,
        origin=uuid4()
    )
    if not valid:
        with pytest.raises(ValidationError):
            value.validate()
    else:
        value.validate()


def test_uuid_validate(sample_database: Root):
    """
    Passes if uuids can be validated.
    Note that this does not check if said uuids reference valid objects
    """
    def replace_origin_with_uuid(entry):
        """Recursively replace origin with a random uuid"""
        if hasattr(entry, 'origin'):
            replace_origin_with_uuid(getattr(entry, 'origin'))
            setattr(entry, 'origin', uuid4())

    for entry in sample_database.entries:
        replace_origin_with_uuid(entry)

    sample_database.validate()
