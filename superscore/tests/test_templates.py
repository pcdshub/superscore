import pytest

from superscore.backends.filestore import FilestoreBackend
from superscore.client import Client
from superscore.model import Collection, Parameter, Template
from superscore.templates import (TemplateMode, fill_template_collection,
                                  find_placeholders, safe_replace,
                                  substitute_placeholders)
from superscore.tests.conftest import setup_test_stack


@pytest.fixture
def basic_template() -> Template:
    param_1 = Parameter(pv_name="MY:PREFIX:MY_PV", description="This is an epics pv")
    param_2 = Parameter(pv_name="MY:PREFIX:MY_PV.mtr1", description="This is an epics pv")
    coll = Collection(title="Collection for my IOC", children=[param_1, param_2])
    phs = {"MY:PREFIX": "prefix", "epics": "shmeckles", "1": "num"}
    template = Template(title="My Template", template_collection=coll,
                        placeholders=phs)

    return template


def test_fill_template(basic_template: Template):
    # apply the placeholders to the tempte collection
    ph_inserted = fill_template_collection(
        basic_template.template_collection,
        basic_template.placeholders,
        mode=TemplateMode.CREATE_PLACEHOLDERS,
        new_uuids=True
    )
    assert ph_inserted.uuid != basic_template.template_collection.uuid
    placeholders = find_placeholders(ph_inserted)
    assert placeholders == set(basic_template.placeholders.values())

    subs = {"prefix": "LCLS", "shmeckles": "TANGO", "num": "42"}
    filled = fill_template_collection(ph_inserted, subs)

    assert filled.title == basic_template.template_collection.title  # no subs
    assert isinstance(filled.children[0], Parameter)
    assert isinstance(filled.children[1], Parameter)
    assert filled.children[0].pv_name == "LCLS:MY_PV"
    assert filled.children[1].pv_name == "LCLS:MY_PV.mtr42"
    assert filled.children[0].description == "This is an TANGO pv"
    assert filled.children[1].description == "This is an TANGO pv"
    assert filled.uuid != basic_template.template_collection.uuid
    assert filled.children[0].uuid != basic_template.template_collection.children[0].uuid


@pytest.mark.parametrize("start,target,replacement,end,", [
    ("no_op", "target", "repl", "no_op"),
    ("my longer sample string", "sample", "{{repl}}", "my longer {{repl}} string"),
    ("my {{ph}} sample {{string}}", "s", "AA", "my {{ph}} AAample {{string}}"),
    ("my {{ph}} sample {{string}}", "ph", "AA", "my {{ph}} sample {{string}}"),
])
def test_safe_replace(start: str, target: str, replacement: str, end: str):
    assert safe_replace(start, target, replacement) == end


@pytest.mark.parametrize("coll,placeholders,", [
    (Collection(), set()),
    (Collection(title="coll title {{ph}}"), {"ph"}),  # basic detection
    (Collection(description="{{desc_a}}", children=[  # duplication
        Parameter(pv_name="{{prefix_a}}:endof"),
        Parameter(pv_name="{{prefix_a}}:other"),
    ]), {"desc_a", "prefix_a"}),
    (Collection(description="{{desc_b}}", children=[  # deeper nesting
        Collection(children=[
            Parameter(pv_name="{{prefix_b}}:endof"),
        ])
    ]), {"desc_b", "prefix_b"}),

])
def test_find_placeholders(coll: Collection, placeholders: set[str]):
    assert find_placeholders(coll) == placeholders


@pytest.mark.parametrize("coll,subs,end_coll,", [
    (
        Collection(
            description="{{desc}}", children=[
                Parameter(pv_name="{{prefix_a}}:endof"),
                Parameter(pv_name="{{prefix_a}}:other"),
            ]
        ),
        {"desc": "description", "prefix_a": "MY:PREFIX"},
        Collection(
            description="description", children=[
                Parameter(pv_name="MY:PREFIX:endof"),
                Parameter(pv_name="MY:PREFIX:other"),
            ]
        ),
    ),  # basic use case
    (
        Collection(description="{{desc}}, placeholder 2 {{final}}"),
        {"desc": "description", "final": "ending phrase"},
        Collection(description="description, placeholder 2 ending phrase"),
    )  # multiple replacements
])
def test_substitute_placeholders(
    coll: Collection, subs: dict[str, str], end_coll: Collection
):
    # unify uuid and creation time for comparison's sake
    end_coll.uuid = coll.uuid
    end_coll.creation_time = coll.creation_time
    for start_entry, end_entry in zip(coll.walk_children(), end_coll.walk_children()):
        end_entry.uuid = start_entry.uuid
        end_entry.creation_time = start_entry.creation_time

    filled = substitute_placeholders(coll, subs, mode=TemplateMode.FILL_PLACEHOLDERS)
    assert filled == end_coll


@setup_test_stack(sources=["db/filestore.json"], backend_type=FilestoreBackend)
def test_client_template(test_client: Client):
    param = Parameter(pv_name="MY:PREFIX:PV", description="desc")
    coll = Collection(title="Collection 1", children=[param,])

    template = test_client.convert_to_template(coll)
    template.placeholders = {"MY:PREFIX": "prefix", "Collection": "id"}
    assert isinstance(template, Template)
    assert coll.title == template.template_collection.title
    assert coll.uuid == template.template_collection.uuid

    filled = test_client.fill_template(template, {"id": "42", "prefix": "X"})
    assert filled.title == "42 1"
    assert isinstance(filled.children[0], Parameter)
    assert filled.children[0].pv_name == "X:PV"

    assert test_client.verify(filled) is True

    # Test verify failure with missing substitutions
    partially_filled = test_client.fill_template(template, {"id": "42"})
    assert test_client.verify(partially_filled) is False
