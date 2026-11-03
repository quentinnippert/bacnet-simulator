from pathlib import Path

import pytest

from bacnet_lab.adapters.bacnet.device_factory import load_all_devices, load_device_from_yaml
from bacnet_lab.domain.enums import PointType


def test_load_device_from_yaml():
    path = Path("config/devices/ahu_01.yaml")
    device = load_device_from_yaml(path)

    assert device.device_id == 1001
    assert device.name == "AHU-01"
    assert len(device.points) == 26
    assert device.get_point_by_name("AHU-01/RoomDifferentialPressure") is None
    assert device.get_point_by_name("AHU-01/OutdoorAirHumidity") is None
    assert all(
        not any(tag in point.description for tag in ("GT81", "GM3", "GF42", "MQ41", "SO1", "P1"))
        for point in device.points
    )

    supply_temp = device.get_point_by_name("AHU-01/SupplyAirTemp")
    assert supply_temp is not None
    assert supply_temp.object_type == PointType.ANALOG_INPUT
    assert supply_temp.present_value == 22.5


def test_load_all_devices():
    devices = load_all_devices("config/devices")
    assert len(devices) == 8

    device_ids = {d.device_id for d in devices}
    assert device_ids == {1001, 2001, 2002, 3001, 4001, 5001, 5002, 6001}


def test_supply_fan_inventory_and_default_ports():
    devices = load_all_devices("config/devices")
    assert {device.name: 47808 + index for index, device in enumerate(devices)} == {
        "AHU-01": 47808,
        "CO2-01": 47809,
        "FCU-01": 47810,
        "FCU-02": 47811,
        "OAT-01": 47812,
        "TSTAT-01": 47813,
        "ZC-01": 47814,
        "SF-01": 47815,
    }
    device = devices[-1]
    assert device.device_id == 6001
    assert len(device.points) == 22
    assert all("exhaust" not in point.object_name.lower() for point in device.points)
    for suffix, point_type in {
        "FanSpeed": PointType.ANALOG_OUTPUT,
        "DamperPosition": PointType.ANALOG_OUTPUT,
        "FanEnable": PointType.BINARY_OUTPUT,
        "FanFaultReset": PointType.BINARY_OUTPUT,
        "FanSpeedFeedback": PointType.ANALOG_INPUT,
        "Airflow": PointType.ANALOG_INPUT,
        "DuctPressure": PointType.ANALOG_INPUT,
        "FanCurrent": PointType.ANALOG_INPUT,
        "FanElectricalPower": PointType.ANALOG_INPUT,
        "FanElectricalEnergy": PointType.ANALOG_INPUT,
        "FanRuntime": PointType.ANALOG_INPUT,
        "FanRunStatus": PointType.BINARY_INPUT,
        "FanFault": PointType.BINARY_INPUT,
        "AirflowProof": PointType.BINARY_INPUT,
        "DamperOpenStatus": PointType.BINARY_INPUT,
        "FanLocalOverride": PointType.BINARY_INPUT,
        "DuctPressureSetpoint": PointType.ANALOG_VALUE,
        "AirflowSetpoint": PointType.ANALOG_VALUE,
    }.items():
        point = device.get_point_by_name(f"SF-01/Supply{suffix}")
        assert point is not None
        assert point.object_type == point_type
        assert point.commandable == (
            point_type not in (PointType.ANALOG_INPUT, PointType.BINARY_INPUT)
        )
    mode = device.get_point_by_name("SF-01/Mode")
    assert mode is not None
    assert mode.state_text == ["Off", "SupplyOnly"]
    assert mode.present_value == 2


@pytest.mark.asyncio
async def test_supply_fan_bacnet_objects():
    from bacpypes3.basetypes import EngineeringUnits

    from bacnet_lab.adapters.bacnet.object_builder import build_local_object

    device = load_device_from_yaml(Path("config/devices/zone_supply_fan_01.yaml"))
    for point in device.points:
        obj = build_local_object(point)
        assert obj.objectName == point.object_name
        value = int(obj.presentValue) if isinstance(point.present_value, bool) else obj.presentValue
        assert value == pytest.approx(float(point.present_value))
        assert obj.description == point.description
        if point.units:
            assert obj.units == EngineeringUnits(point.units)
            assert obj.covIncrement == pytest.approx(point.cov_increment)
        if point.commandable:
            assert len(obj.priorityArray) == 16
            default = (
                int(obj.relinquishDefault)
                if isinstance(point.present_value, bool)
                else obj.relinquishDefault
            )
            assert default == pytest.approx(float(point.present_value))


def test_load_all_devices_missing_dir():
    with pytest.raises(ValueError, match="directory does not exist"):
        load_all_devices("nonexistent_dir")


@pytest.mark.parametrize(
    "extra",
    [
        "cov_increment: .inf",
        "cov_increment: 1.0e100",
        "cov_increment: true",
        'state_text: "off,on"',
    ],
)
def test_invalid_point_metadata_fails_at_configuration_load(tmp_path, extra):
    path = tmp_path / "bad.yaml"
    path.write_text(
        f"device_id: 1\nname: Test\npoints:\n  - object_type: analogInput\n    object_name: Temp\n    object_instance: 1\n    {extra}\n"
    )
    with pytest.raises(ValueError, match="Invalid device configuration"):
        load_device_from_yaml(path)


def test_empty_explicit_address_is_not_silently_ignored(tmp_path):
    path = tmp_path / "bad.yaml"
    path.write_text("device_id: 1\nname: Test\naddress: {}\n")
    with pytest.raises(ValueError, match="address requires"):
        load_device_from_yaml(path)
