import apischema

from superscore.model import (Collection, Parameter, Readback, Root, Setpoint,
                              Severity, Snapshot, Status)


def test_serialize_collection_roundtrip():
    p1 = Parameter(pv_name="TEST:PV1", description="First test Parameter")
    p2 = Parameter(pv_name="TEST:PV2", description="Second test Parameter")
    p3 = Parameter(pv_name="TEST:PV3", description="Third test Parameter")
    p4 = Parameter(pv_name="TEST:PV4", description="Fourth test Parameter")
    c1 = Collection(title="Collection 1", description="Inner Collection", children=[p1, p2])
    c2 = Collection(title="Collection 2", description="Outer Collection", children=[p3, c1, p4])
    serial = apischema.serialize(Collection, c2)
    deserialized = apischema.deserialize(Collection, serial)
    assert deserialized == c2
    assert deserialized.children[0] == p3
    assert deserialized.children[1] == c1
    assert deserialized.children[2] == p4
    assert deserialized.children[1].children[0] == p1
    assert deserialized.children[1].children[1] == p2


def test_serialize_snapshot_roundtrip():
    v1 = Setpoint(pv_name="TEST:PV1", description="First test Value", data=4, status=Status.NO_ALARM, severity=Severity.NO_ALARM)
    v2 = Setpoint(pv_name="TEST:PV2", description="Second test Value", data=1.8, status=Status.UDF, severity=Severity.INVALID)
    v3 = Setpoint(pv_name="TEST:PV3", description="Third test Value", data="TRIM", status=Status.DISABLE, severity=Severity.NO_ALARM)
    v4 = Setpoint(pv_name="TEST:PV4", description="Fourth test Value", data=False, status=Status.HIGH, severity=Severity.MAJOR)
    v5 = Setpoint(pv_name="TEST:PV2", description="Fifth test Value", data=None, status=Status.UDF, severity=Severity.INVALID)
    s1 = Snapshot(title="Snapshot 1", description="Snapshot of Inner Collection", children=[v1, v2])
    s2 = Snapshot(title="Snapshot 2", description="Snapshot of Outer Collection", children=[v3, s1, v4, v5])
    serial = apischema.serialize(Snapshot, s2)
    deserialized = apischema.deserialize(Snapshot, serial)
    assert deserialized == s2
    assert deserialized.children[0] == v3
    assert deserialized.children[1] == s1
    assert deserialized.children[2] == v4
    assert deserialized.children[3] == v5
    assert deserialized.children[1].children[0] == v1
    assert deserialized.children[1].children[1] == v2


def test_sample_database_roundtrip(sample_database: Root):
    ser = apischema.serialize(Root, sample_database)
    deser = apischema.deserialize(Root, ser)
    assert deser == sample_database


class TestEntryValidation:
    @staticmethod
    def test_parameter_readback_validation():
        readback_pv = Parameter(
            pv_name="TEST:PV:READBACK",
            description="Used as a readback for another PV",
        )
        main_pv = Parameter(
            pv_name="TEST:PV:MAIN",
            description="A PV with a separate readback",
            readback=readback_pv,
        )
        assert readback_pv.validate()
        assert main_pv.validate()

        readback_pv.abs_tolerance = "1"
        assert not main_pv.validate()

    @staticmethod
    def test_setpoint_validation():
        readback = Readback(
            pv_name="TEST:PV:READBACK",
            description="Used as a readback for another PV",
            data=0.0,
        )
        setpoint = Setpoint(
            pv_name="TEST:PV:SETPOINT",
            description="A PV with a separate readback",
            data=5.0,
            readback=readback,
            creation_time=readback.creation_time,
        )
        assert readback.validate()
        assert setpoint.validate()

        readback.rel_tolerance = "10%"
        assert not setpoint.validate()

    @staticmethod
    def test_nestable_empty_validation():
        empty_col = Collection(
            title="Emtpy Collection",
            description="A Collection without any children",
            children=[],
        )
        assert empty_col.validate()

        parent_col = Collection(
            title="Non-empty Collection",
            description="A Collection whose child is empty",
            children=[empty_col],
        )
        assert parent_col.validate()

    @staticmethod
    def test_nestable_cycle_validation():
        pv = Parameter(
            pv_name="TEST:PV:1",
            description="An ordinary, valid PV",
        )
        col = Collection(
            title="Collection",
            description="A valid Collection that becomes invalid when it becomes its own parent",
            children=[pv]
        )
        assert col.validate()

        col.children.append(col)
        assert not col.validate()

        # ensure there's no hysteresis in cycle detection
        col.children.remove(col)
        assert col.validate()

    @staticmethod
    def test_collection_reachable_from_snapshot_validation():
        pv = Parameter(
            pv_name="TEST:PV:1",
            description="An ordinary, valid PV",
        )
        col = Collection(
            title="Collection",
            description="An ordinary, valid Collection",
            children=[pv]
        )
        assert col.validate()

        setpoint = Setpoint(
            pv_name=pv.pv_name,
            description=pv.description,
            data=0,
        )
        snapshot = Snapshot(
            title="Snapshot",
            description="A valid Snapshot that becomes invalid when it gains a child Collection",
            children=[setpoint]
        )
        assert snapshot.validate()

        snapshot.children.append(col)
        assert not snapshot.validate()

    @staticmethod
    def test_fixture_validation(linac_backend):
        linac_model = linac_backend.get_entry("441ff79f-4948-480e-9646-55a1462a5a70")
        assert linac_model.validate()

        linac_snapshot = linac_backend.get_entry("06282731-33ea-4270-ba14-098872e627dc")
        assert linac_snapshot.validate()
