import aioca
import pytest


@pytest.mark.parametrize("ioc", ["linac"], indirect=True)
async def test_ioc(ioc):
    assert await aioca.caget("SCORETEST:MGNT:GUNB:TEST0") is not None
