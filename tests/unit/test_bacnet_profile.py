import asyncio

import pytest
from bacpypes3.errors import PropertyError
from bacpypes3.primitivedata import Boolean, Null, Real, Unsigned

from bacnet_lab.adapters.bacnet.device_factory import load_all_devices
from bacnet_lab.adapters.bacnet.object_builder import build_local_object
from bacnet_lab.adapters.bacnet.profile import SimulatorDeviceObject


@pytest.fixture
async def output():
    obj = build_local_object(
        load_all_devices("config/devices")[0].get_point_by_name("AHU-01/CoolingValve")
    )
    yield obj
    await asyncio.sleep(0)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "attr,value,index,priority,error",
    [
        ("presentValue", Real(80), None, 6, "writeAccessDenied"),
        ("presentValue", Real(80), 1, 8, "propertyIsNotAnArray"),
        ("presentValue", Real(80), None, 0, "valueOutOfRange"),
        ("presentValue", Real(80), None, 17, "valueOutOfRange"),
        ("relinquishDefault", Real(101), None, None, "valueOutOfRange"),
        ("covIncrement", Real(-1), None, None, "writeAccessDenied"),
        ("statusFlags", None, None, None, "writeAccessDenied"),
    ],
)
async def test_protocol_rejects_invalid_or_readonly_writes(
    output, attr, value, index, priority, error
):
    with pytest.raises(PropertyError) as caught:
        await output.write_property(attr, value, index, priority)
    assert caught.value.errorCode == error
    assert output.presentValue == 45


@pytest.mark.asyncio
async def test_relinquish_default_recalculates_but_does_not_override_commands(output):
    await output.write_property("relinquishDefault", Real(25))
    assert output.presentValue == 25
    await output.write_property("presentValue", Real(80), priority=8)
    await output.write_property("relinquishDefault", Real(35))
    assert output.presentValue == 80
    await output.write_property("presentValue", Null(()), priority=8)
    assert output.presentValue == 35


@pytest.mark.asyncio
async def test_input_is_isolated_from_simulation_while_out_of_service():
    obj = build_local_object(load_all_devices("config/devices")[0].points[0])
    with pytest.raises(PropertyError):
        await obj.write_property("presentValue", Real(66))
    await obj.write_property("outOfService", Boolean(True))
    await obj.write_property("presentValue", Real(66))
    obj.update_sensor(18.0)
    assert obj.presentValue == 66 and list(obj.statusFlags) == [0, 0, 0, 1]
    await obj.write_property("outOfService", Boolean(False))
    assert obj.presentValue == 18 and list(obj.statusFlags) == [0, 0, 0, 0]


@pytest.mark.asyncio
async def test_device_advertises_supported_types_and_protects_identity():
    obj = SimulatorDeviceObject(objectIdentifier=("device", 123), objectName="Test")
    assert obj.protocolObjectTypesSupported[0] == 1
    assert obj.protocolObjectTypesSupported[19] == 1
    assert obj.protocolObjectTypesSupported[56] == 1
    assert obj.protocolObjectTypesSupported[17] == 0
    with pytest.raises(PropertyError):
        await obj.write_property("vendorIdentifier", Unsigned(123))
