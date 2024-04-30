import apischema

from superscore.model import (Collection, Parameter, Severity, Snapshot,
                              Status, Value)


def test_serialize_collection_roundtrip():
    p1 = Parameter(pv_name="TEST:PV1", description="First test Parameter")
    p2 = Parameter(pv_name="TEST:PV2", description="Second test Parameter")
    p3 = Parameter(pv_name="TEST:PV3", description="Third test Parameter")
    p4 = Parameter(pv_name="TEST:PV4", description="Fourth test Parameter")
    c1 = Collection(title="Collection 1", description="Inner Collection", children=[p1, p2])
    c2 = Collection(title="Collection 2", description="Outer Collection", children=[p3, c1, p4])
    serial = apischema.serialize(c2)
    deserialized = apischema.deserialize(Collection, serial)
    assert deserialized == c2
    assert deserialized.children[0] == p3
    assert deserialized.children[1] == c1
    assert deserialized.children[2] == p4
    assert deserialized.children[1].children[0] == p1
    assert deserialized.children[1].children[1] == p2


def test_serialize_snapshot_roundtrip():
    v1 = Value(pv_name="TEST:PV1", description="First test Value", data=4, status=Status.NO_ALARM, severity=Severity.NO_ALARM)
    v2 = Value(pv_name="TEST:PV2", description="Second test Value", data=1.8, status=Status.UDF, severity=Severity.INVALID)
    v3 = Value(pv_name="TEST:PV3", description="Third test Value", data="TRIM", status=Status.DISABLE, severity=Severity.NO_ALARM)
    v4 = Value(pv_name="TEST:PV4", description="Fourth test Value", data=False, status=Status.HIGH, severity=Severity.MAJOR)
    s1 = Snapshot(title="Snapshot 1", description="Snapshot of Inner Collection", children=[v1, v2])
    s2 = Snapshot(title="Snapshot 2", description="Snapshot of Outer Collection", children=[v3, s1, v4])
    serial = apischema.serialize(s2)
    deserialized = apischema.deserialize(Snapshot, serial)
    assert deserialized == s2
    assert deserialized.children[0] == v3
    assert deserialized.children[1] == s1
    assert deserialized.children[2] == v4
    assert deserialized.children[1].children[0] == v1
    assert deserialized.children[1].children[1] == v2
