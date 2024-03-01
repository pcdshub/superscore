import pytest

from superscore.model import Collection, Parameter, Root, Snapshot, Value


@pytest.fixture(scope='function')
def sample_database():
    """
    A sample superscore database, including all the Entry types.
    Corresponds to a caproto.ioc_examples.fake_motor_record, which mimics an IMS
    motor record
    """
    root = Root()

    param_1 = Parameter(
        name='parameter 1',
        description='parameter in root',
        pv_name='MY:MOTOR:mtr1.ACCL'
    )
    root.entries.append(param_1)

    value_1 = Value.from_parameter(
        origin=param_1,
        data=2,
    )
    root.entries.append(value_1)

    coll_1 = Collection(
        name='collection 1',
        description='collection defining some motor fields',
    )
    snap_1 = Snapshot(
        name='snapshot 1',
        description='Snapshot created from collection 1',
    )
    for fld, data in zip(['ACCL', 'VELO', 'PREC'], [2, 2, 6]):  # Defaults[1, 1, 3]
        sub_param = Parameter(
            name=f'coll_1_field_{fld}',
            description=f'motor field {fld}',
            pv_name=f'MY:PREFIX:mtr1.{fld}'
        )
        sub_value = Value.from_parameter(
            origin=sub_param,
            data=data,
        )

        coll_1.parameters.append(sub_param)
        snap_1.values.append(sub_value)

    root.entries.append(coll_1)
    root.entries.append(snap_1)

    return root
