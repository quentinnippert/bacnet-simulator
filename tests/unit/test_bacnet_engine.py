import pytest
from bacpypes3.app import Application
from bacpypes3.local.device import DeviceObject
from bacpypes3.local.networkport import NetworkPortObject
from bacpypes3.pdu import IPv4Address
from bacpypes3.primitivedata import PropertyIdentifier, Real
from bacpypes3.service.object import read_property_to_result_element

from bacnet_lab.adapters.bacnet.device_factory import load_all_devices
from bacnet_lab.adapters.bacnet.engine import BACnetEngine, Runtime
from bacnet_lab.adapters.bacnet.object_builder import build_local_object
from bacnet_lab.domain.enums import PointType


@pytest.mark.asyncio
async def test_optional_bbmd_address_is_absent_and_readable_as_error():
    port = NetworkPortObject(
        IPv4Address("127.0.0.1/32:47808"), objectIdentifier=("networkPort", 1), objectName="network"
    )
    result = await read_property_to_result_element(port, PropertyIdentifier("fdBBMDAddress"))
    assert str(result.readResult.propertyAccessError.errorCode) == "unknown-property"


@pytest.mark.asyncio
async def test_real_objects_have_cov_and_complete_multistate_properties():
    devices = load_all_devices("config/devices")
    for device in devices:
        for point in device.points:
            obj = build_local_object(point)
            if point.object_type.value.startswith("analog"):
                assert obj.covIncrement == pytest.approx(point.cov_increment)
            if point.state_text:
                assert list(obj.stateText) == point.state_text
                assert obj.numberOfStates == len(point.state_text)


@pytest.mark.asyncio
async def test_engine_reads_effective_priority_and_relinquishes():
    device = load_all_devices("config/devices")[0]
    point = device.get_point_by_name("AHU-01/CoolingValve")
    obj = build_local_object(point)
    app = Application.from_object_list(
        [DeviceObject(objectIdentifier=("device", device.device_id), objectName=device.name), obj]
    )
    engine = BACnetEngine()
    engine._runtimes[device.device_id] = Runtime({point.object_name: obj}, app)
    await obj.write_property("presentValue", Real(88), priority=8)
    assert await engine.read_point_value(1001, PointType.ANALOG_OUTPUT, 1) == 88
    await engine.write_point_value(1001, PointType.ANALOG_OUTPUT, 1, 55)
    assert await engine.read_point_value(1001, PointType.ANALOG_OUTPUT, 1) == 88
    await engine.write_point_value(1001, PointType.ANALOG_OUTPUT, 1, None, priority=8)
    assert await engine.read_point_value(1001, PointType.ANALOG_OUTPUT, 1) == 55
    assert point.present_value == 45  # Adapter never mutates the domain snapshot.
    await engine.stop_all()


@pytest.mark.asyncio
async def test_shutdown_attempts_every_device_after_a_failure():
    from unittest.mock import AsyncMock

    engine = BACnetEngine()
    engine._runtimes = {1: None, 2: None}
    engine.stop_device = AsyncMock(side_effect=[RuntimeError("close failed"), None])
    with pytest.raises(ExceptionGroup):
        await engine.stop_all()
    assert engine.stop_device.await_count == 2
