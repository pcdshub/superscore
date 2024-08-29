from superscore.control_layers.core import ControlLayer


def test_ioc(linac_ioc):
    cl = ControlLayer()
    assert cl.get("SCORETEST:MGNT:GUNB:TEST0").data == 1
    cl.put("SCORETEST:MGNT:GUNB:TEST0", 0)
    assert cl.get("SCORETEST:MGNT:GUNB:TEST0").data == 0

    assert cl.get("SCORETEST:VAC:GUNB:TEST1").data == "Ion Pump"
    cl.put("SCORETEST:VAC:GUNB:TEST1", "new value")
    assert cl.get("SCORETEST:VAC:GUNB:TEST1").data == "new value"

    assert cl.get("SCORETEST:LASR:GUNB:TEST2").data == 5
    cl.put("SCORETEST:LASR:GUNB:TEST2", 10)
    assert cl.get("SCORETEST:LASR:GUNB:TEST2").data == 10

    assert cl.get("SCORETEST:LASR:IN10:TEST0").data == 645.26
    cl.put("SCORETEST:LASR:IN10:TEST0", 600.0)
    assert cl.get("SCORETEST:LASR:IN10:TEST0").data == 600.0
