from bacnet_lab.domain.enums import DeviceStatus, PointType
from bacnet_lab.domain.models.device import Device, Point
from bacnet_lab.domain.value_objects import DeviceAddress


def test_device_creation():
    device = Device(device_id=1001, name="AHU-01", description="Test AHU")
    assert device.device_id == 1001
    assert device.name == "AHU-01"
    assert device.status == DeviceStatus.ONLINE
    assert device.points == []


def test_device_get_point():
    point = Point(
        object_type=PointType.ANALOG_INPUT,
        object_instance=1,
        object_name="AHU-01/SupplyAirTemp",
        present_value=22.5,
    )
    device = Device(device_id=1001, name="AHU-01", points=[point])

    found = device.get_point(PointType.ANALOG_INPUT, 1)
    assert found is not None
    assert found.object_name == "AHU-01/SupplyAirTemp"

    assert device.get_point(PointType.ANALOG_INPUT, 99) is None


def test_device_get_point_by_name():
    point = Point(
        object_type=PointType.ANALOG_INPUT,
        object_instance=1,
        object_name="AHU-01/SupplyAirTemp",
        present_value=22.5,
    )
    device = Device(device_id=1001, name="AHU-01", points=[point])

    found = device.get_point_by_name("AHU-01/SupplyAirTemp")
    assert found is not None
    assert found.present_value == 22.5

    assert device.get_point_by_name("nonexistent") is None


def test_point_object_identifier():
    point = Point(
        object_type=PointType.ANALOG_INPUT,
        object_instance=1,
        object_name="test",
    )
    assert point.object_identifier == "analogInput,1"


def test_device_address():
    addr = DeviceAddress(ip="192.168.1.1", port=47808)
    assert str(addr) == "192.168.1.1:47808"
