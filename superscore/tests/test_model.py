import apischema

from superscore.model import (Collection, Parameter, Root, Setpoint, Severity,
                              Snapshot, Status)


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
    s1 = Snapshot(title="Snapshot 1", description="Snapshot of Inner Collection", children=[v1, v2])
    s2 = Snapshot(title="Snapshot 2", description="Snapshot of Outer Collection", children=[v3, s1, v4])
    serial = apischema.serialize(Snapshot, s2)
    deserialized = apischema.deserialize(Snapshot, serial)
    assert deserialized == s2
    assert deserialized.children[0] == v3
    assert deserialized.children[1] == s1
    assert deserialized.children[2] == v4
    assert deserialized.children[1].children[0] == v1
    assert deserialized.children[1].children[1] == v2


def test_sample_database_roundtrip(sample_database: Root):
    ser = apischema.serialize(Root, sample_database)
    deser = apischema.deserialize(Root, ser)
    assert deser == sample_database


class TestEntryValidation:
    @staticmethod
    def test_fixture_validation(linac_backend):
        linac_model = linac_backend.get_entry("441ff79f-4948-480e-9646-55a1462a5a70")
        assert linac_model.validate()

        linac_snapshot = linac_backend.get_entry("06282731-33ea-4270-ba14-098872e627dc")
        assert linac_snapshot.validate()

    @staticmethod
    def test_parameter_readback_validation(linac_backend):
        vac_gunb_pv1 = linac_backend.get_entry("8f3ac401-68f8-4def-b65a-3c8116c80ba7")
        vac_gunb_pv2 = linac_backend.get_entry("06448272-cd38-4bb4-9b8d-292673a497e9")
        vac_gunb_pv1.readback = vac_gunb_pv2
        assert vac_gunb_pv1.validate()

        vac_gunb_pv2.abs_tolerance = "1"
        assert not vac_gunb_pv1.validate()

    @staticmethod
    def test_setpoint_validation(linac_backend):
        vac_li21_readback = linac_backend.get_entry("de66d08e-09c3-4c45-8978-900e51d00248")
        vac_li21_setpoint = linac_backend.get_entry("4bffe9a5-f198-41d8-90ab-870d1b5a325b")
        assert vac_li21_readback.validate()
        assert vac_li21_setpoint.validate()

        vac_li21_readback.rel_tolerance = "10%"
        assert not vac_li21_setpoint.validate()

    @staticmethod
    def test_nestable_empty_validation(linac_backend):
        linac_model = linac_backend.get_entry("441ff79f-4948-480e-9646-55a1462a5a70")
        vac_bsy_col = linac_backend.get_entry("22c2d597-2139-4c02-ac86-27f474728fad")
        vac_bsy_col.children = []
        assert not linac_model.validate()

    @staticmethod
    def test_nestable_cycle_validation(linac_backend):
        linac_model = linac_backend.get_entry("441ff79f-4948-480e-9646-55a1462a5a70")
        bsy_col = linac_backend.get_entry("2506d87a-5980-4470-b29a-63eea183f53d")
        vac_bsy_col = linac_backend.get_entry("22c2d597-2139-4c02-ac86-27f474728fad")
        vac_bsy_col.children.append(bsy_col)
        assert not linac_model.validate()

        # ensure there's no hysteresis in cycle detection
        vac_bsy_col.children.remove(bsy_col)
        assert linac_model.validate()

    @staticmethod
    def test_collection_reachable_from_snapshot_validation(linac_backend):
        linac_snapshot = linac_backend.get_entry("06282731-33ea-4270-ba14-098872e627dc")
        bsy_snapshot = linac_backend.get_entry("a62f1386-39de-4d19-9ea4-82f0212169a7")
        vac_bsy_col = linac_backend.get_entry("22c2d597-2139-4c02-ac86-27f474728fad")
        bsy_snapshot.children.append(vac_bsy_col)
        assert not linac_snapshot.validate()
