import shutil
from pathlib import Path
from typing import List

import pytest

from superscore.backends.core import _Backend
from superscore.backends.filestore import FilestoreBackend
from superscore.backends.test import TestBackend
from superscore.model import Collection, Parameter, Root, Setpoint, Snapshot


@pytest.fixture
def linac_backend():
    lasr_gunb_pv1 = Parameter(
        uuid="5544c58f-88b6-40aa-9076-f180a44908f5",
        pv_name="LASR:GUNB:TEST1",
        description="First LASR pv in GUNB",
    )

    now = lasr_gunb_pv1.creation_time

    lasr_gunb_pv2 = Parameter(
        uuid="7cb3760c-793c-4974-a8ae-778e5d491e4a",
        pv_name="LASR:GUNB:TEST2",
        description="Second LASR pv in GUNB",
        creation_time=now
    )

    lasr_gunb_col = Collection(
        uuid="d5bade05-d992-4e44-87d8-0db2937209bf",
        description="LASR devices within GUNB",
        creation_time=now,
        title="LASR",
        children=[
            lasr_gunb_pv1,
            lasr_gunb_pv2,
        ]
    )

    mgnt_gunb_pv = Parameter(
        uuid="930b137f-5ae2-470e-8b82-c4b4eb7e639e",
        pv_name="MGNT:GUNB:TEST0",
        description="Only MGNT pv in GUNB",
        creation_time=now
    )

    mgnt_gunb_col = Collection(
        uuid="981d52d1-4d3c-4f85-89d7-8c04a0d588d0",
        description="MGNT devices within GUNB",
        creation_time=now,
        title="MGNT",
        children=[
            mgnt_gunb_pv,
        ]
    )

    vac_gunb_pv1 = Parameter(
        uuid="8f3ac401-68f8-4def-b65a-3c8116c80ba7",
        pv_name="VAC:GUNB:TEST1",
        description="First VAC pv in GUNB",
        creation_time=now
    )

    vac_gunb_pv2 = Parameter(
        uuid="06448272-cd38-4bb4-9b8d-292673a497e9",
        pv_name="VAC:GUNB:TEST2",
        description="Second VAC pv in GUNB",
        creation_time=now
    )

    vac_gunb_col = Collection(
        uuid="e09cf046-fbf6-4d37-9ee1-c3c2dd977798",
        description="VAC devices within GUNB",
        creation_time=now,
        title="VAC",
        children=[
            vac_gunb_pv1,
            vac_gunb_pv2,
        ]
    )

    gunb_col = Collection(
        uuid="6f09255f-3424-4fc2-bbd7-ae677c8a06b9",
        description="Injector sector for LCLS-SC",
        creation_time=now,
        title="GUNB",
        children=[
            vac_gunb_col,
            mgnt_gunb_col,
            lasr_gunb_col,
        ]
    )

    vac_l0b_pv = Parameter(
        uuid="5ec33c74-7f4c-4905-a106-44fbfe138140",
        pv_name="VAC:L0B:TEST0",
        description="Only VAC pv in L0B",
        creation_time=now
    )

    vac_l0b_col = Collection(
        uuid="aa11f29a-3e7e-4647-bfc9-133257647fb7",
        description="First transport sector for LCLS-SC",
        creation_time=now,
        title="VAC",
        children=[
            vac_l0b_pv,
        ]
    )

    l0b_col = Collection(
        uuid="5e84544b-4cfa-471c-b827-80063801d27b",
        description="First transport sector for LCLS-SC",
        creation_time=now,
        title="L0B",
        children=[
            vac_l0b_col,
        ]
    )

    vac_bsy_pv = Parameter(
        uuid="030786df-153b-4d29-bc1f-66deeb116724",
        pv_name="VAC:BSY:TEST0",
        description="Only VAC pv in BSY",
        creation_time=now
    )

    vac_bsy_col = Collection(
        uuid="22c2d597-2139-4c02-ac86-27f474728fad",
        description="Vacuum devices in the BSY",
        creation_time=now,
        title="VAC",
        children=[
            vac_bsy_pv,
        ]
    )

    bsy_col = Collection(
        uuid="2506d87a-5980-4470-b29a-63eea183f53d",
        description="Sector in which beam is directed towards an endpoint",
        creation_time=now,
        title="BSY",
        children=[
            vac_bsy_col,
        ]
    )

    lcls_sc_col = Collection(
        uuid="4732fed6-c321-4a5c-b45b-c2bf704b7fe3",
        description="The superconducting LINAC",
        creation_time=now,
        title="LCLS-SC",
        children=[
            gunb_col,
            l0b_col,
            bsy_col,
        ]
    )

    vac_li10_pv = Parameter(
        uuid="2c83a9be-bec6-4436-8233-79df300af670",
        pv_name="VAC:LI10:TEST0",
        description="Only VAC pv in LI10",
        creation_time=now
    )

    vac_li10_col = Collection(
        uuid="214ec7c5-29d5-4827-b9dc-8da00664b462",
        description="Vacuum devices in LI10",
        creation_time=now,
        title="VAC",
        children=[
            vac_li10_pv,
        ]
    )

    li10_col = Collection(
        uuid="596c4935-92eb-4bfd-a96e-b38f55f6c0a4",
        description="First transport sector for FACET",
        creation_time=now,
        title="LI10",
        children=[
            vac_li10_col,
        ]
    )

    lasr_in10_pv = Parameter(
        uuid="f802dee1-569b-4c6b-a32f-c213af10ecec",
        pv_name="LASR:IN10:TEST0",
        description="Only laser pv in IN10",
        creation_time=now
    )

    lasr_in10_col = Collection(
        uuid="213b8629-8b6d-4b2a-a7a4-0201a568e8cd",
        description="Laser devices in IN10",
        creation_time=now,
        title="LASR",
        children=[
            lasr_in10_pv,
        ]
    )

    in10_col = Collection(
        uuid="8395ad87-b9e9-4064-8996-316ccce9dc27",
        description="Injector sector for FACET",
        creation_time=now,
        title="IN10",
        children=[
            lasr_in10_col,
        ]
    )

    facet_col = Collection(
        uuid="fe9485e0-bc36-45a4-89ec-31a4fc92ef7b",
        description="The FACET LINAC",
        creation_time=now,
        title="FACET",
        children=[
            in10_col,
            li10_col,
        ]
    )

    lasr_in20_pv = Parameter(
        uuid="a13ef8a5-b8df-4caa-80f5-395b16eaa5f1",
        pv_name="LASR:IN20:TEST0",
        description="Only laser pv in IN20",
        creation_time=now
    )

    lasr_in20_col = Collection(
        uuid="2290a098-0475-403d-a902-a26481068f25",
        description="Laser devices in IN20",
        creation_time=now,
        title="LASR",
        children=[
            lasr_in20_pv,
        ]
    )

    in20_col = Collection(
        uuid="4cd08663-ee26-41ed-87d2-5ff0777e0e35",
        description="Injector sector for LCLS-NC",
        creation_time=now,
        title="IN20",
        children=[
            lasr_in20_col,
        ]
    )

    vac_li21_pv = Parameter(
        uuid="8dba63d5-98e8-4647-ae44-ff0a38a4805d",
        pv_name="VAC:LI21:TEST0",
        description="Only VAC pv in LI21",
        creation_time=now
    )

    vac_li21_col = Collection(
        uuid="be3d4655-7813-4974-bb10-19e4787f8a8e",
        description="VAC devices within LI21",
        creation_time=now,
        title="VAC",
        children=[
            vac_li21_pv,
        ]
    )

    li21_col = Collection(
        uuid="8b434f17-fc67-430c-aa33-d1afb64dbad2",
        description="First transport sector for LCLS-NC",
        creation_time=now,
        title="LI21",
        children=[
            vac_li21_col,
        ]
    )

    lcls_nc_col = Collection(
        uuid="973ce16b-61ff-469b-a5f2-cd64783dcec5",
        description="The normal-conducting LINAC",
        creation_time=now,
        title="LCLS-NC",
        children=[
            in20_col,
            li21_col,
            bsy_col,
        ]
    )

    root_col = Collection(
        uuid="441ff79f-4948-480e-9646-55a1462a5a70",
        description="All three facilities in the SLAC LINAC: LCLS-NC, FACET, and LCLS-SC",
        title="Accelerator Directorate",
        children=[
            lcls_nc_col,
            facet_col,
            lcls_sc_col,
        ]
    )

    return TestBackend([root_col])


@pytest.fixture(scope='function')
def sample_database() -> Root:
    """
    A sample superscore database, including all the Entry types.
    Corresponds to a caproto.ioc_examples.fake_motor_record, which mimics an IMS
    motor record
    """
    root = Root()
    param_1 = Parameter(
        description='parameter 1 in root',
        pv_name='MY:MOTOR:mtr1.ACCL'
    )
    root.entries.append(param_1)
    value_1 = Setpoint.from_parameter(
        origin=param_1,
        data=2,
    )
    root.entries.append(value_1)
    coll_1 = Collection(
        title='collection 1',
        description='collection 1 defining some motor fields',
    )
    snap_1 = Snapshot(
        title='snapshot 1',
        description='Snapshot 1 created from collection 1',
    )
    for fld, data in zip(['ACCL', 'VELO', 'PREC'], [2, 2, 6]):  # Defaults[1, 1, 3]
        sub_param = Parameter(
            description=f'motor field {fld}',
            pv_name=f'MY:PREFIX:mtr1.{fld}'
        )
        sub_value = Setpoint.from_parameter(
            origin=sub_param,
            data=data,
        )
        coll_1.children.append(sub_param)
        snap_1.children.append(sub_value)
    root.entries.append(coll_1)
    root.entries.append(snap_1)

    return root


@pytest.fixture(scope='function')
def filestore_backend(tmp_path: Path) -> FilestoreBackend:
    fp = Path(__file__).parent / 'db' / 'filestore.json'
    tmp_fp = tmp_path / 'tmp_filestore.json'
    shutil.copy(fp, tmp_fp)
    print(tmp_path)
    return FilestoreBackend(path=tmp_fp)


@pytest.fixture(scope='function')
def test_backends(filestore_backend: FilestoreBackend) -> List[_Backend]:
    return [filestore_backend,]


@pytest.fixture
def backends(request, test_backends: List[_Backend]):
    i = request.param
    return test_backends[i]
