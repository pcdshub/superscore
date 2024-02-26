from typing import Any

import pytest

from superscore.model import Root


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

    with pytest.raises(TypeError):
        sample_database.validate()
    with pytest.raises(TypeError):
        entry.validate()


def test_backend_load():
    assert True
