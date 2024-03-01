import json
from typing import Any

import pytest
from apischema import ValidationError, deserialize, serialize

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
    """Passes if improper types fail to validate"""
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
        [object(), False], [Root(), False]
    ]
)
def test_epics_type_validate(data: Any, valid: bool):
    """Passes if EPICS types are validated correctly"""
    if not valid:
        with pytest.raises(TypeError):
            Value(
                name='My Value',
                description='description value',
                data=data,
            )
    else:
        Value(
            name='My Value',
            description='description value',
            data=data,
        )


def test_serialization_roundtrip(sample_database, tmp_path):
    """Passes if serialization and deserialization works"""
    serialized_db = serialize(Root, sample_database)
    with open(tmp_path / 'db.txt', 'w') as fs:
        json.dump(serialized_db, fs, indent=2)

    with open(tmp_path / 'db.txt', 'r') as fd:
        loaded_db = json.load(fd)

    deserialized_db = deserialize(Root, loaded_db)

    assert deserialized_db == sample_database
