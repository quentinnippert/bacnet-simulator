from __future__ import annotations

import asyncio
import logging

from bacnet_lab.domain.enums import PointType
from bacnet_lab.domain.models.device import Device
from bacnet_lab.domain.value_objects import DeviceAddress, PointValue
from bacnet_lab.ports.device_network import DeviceNetworkPort

logger = logging.getLogger(__name__)


class BAC0Engine(DeviceNetworkPort):
    """Manages one BAC0 lite instance per device on separate UDP ports."""

    def __init__(self, ip: str = "0.0.0.0") -> None:
        self._ip = ip
        self._instances: dict[int, object] = {}  # device_id -> BAC0 instance
        self._devices: dict[int, Device] = {}

    async def start_device(self, device: Device, udp_port: int) -> None:
        try:
            import BAC0

            loop = asyncio.get_event_loop()
            instance = await loop.run_in_executor(
                None,
                lambda: BAC0.lite(
                    ip=self._ip,
                    port=udp_port,
                    deviceId=device.device_id,
                    localObjName=device.name,
                ),
            )

            from bacnet_lab.adapters.bacnet.object_builder import build_local_object_config

            for point in device.points:
                config = build_local_object_config(point)
                try:
                    await loop.run_in_executor(
                        None,
                        lambda c=config: self._create_local_object(instance, c),
                    )
                except Exception as e:
                    logger.warning(
                        "Failed to create object %s on device %d: %s",
                        point.object_name, device.device_id, e,
                    )

            self._instances[device.device_id] = instance
            self._devices[device.device_id] = device
            device.address = DeviceAddress(ip=self._ip, port=udp_port)
            logger.info(
                "Started BACnet device %s (ID=%d) on port %d",
                device.name, device.device_id, udp_port,
            )
        except Exception as e:
            logger.error("Failed to start BACnet device %d: %s", device.device_id, e)
            raise

    def _create_local_object(self, instance: object, config: dict) -> None:
        """Create a local BACnet object on a BAC0 instance."""
        import BAC0

        obj_type = config["object_type"]
        pv = config["presentValue"]

        if "analog" in obj_type.lower():
            _cls = BAC0.local.analogValue.create_AV
            if "input" in obj_type.lower():
                _cls = BAC0.local.analogInput.create_AI
            elif "output" in obj_type.lower():
                _cls = BAC0.local.analogOutput.create_AO
            _cls(
                instance=config["instance"],
                name=config["name"],
                description=config.get("description", ""),
                presentValue=float(pv) if not isinstance(pv, bool) else 0.0,
                properties={"units": config.get("units", "noUnits")},
                is_commandable=("output" in obj_type.lower() or "value" in obj_type.lower()),
            )
        elif "binary" in obj_type.lower():
            _cls = BAC0.local.binaryValue.create_BV
            if "input" in obj_type.lower():
                _cls = BAC0.local.binaryInput.create_BI
            elif "output" in obj_type.lower():
                _cls = BAC0.local.binaryOutput.create_BO
            _cls(
                instance=config["instance"],
                name=config["name"],
                description=config.get("description", ""),
                presentValue=bool(pv),
                is_commandable=("output" in obj_type.lower() or "value" in obj_type.lower()),
            )
        elif "multiState" in obj_type:
            _cls = BAC0.local.multiStateValue.create_MSV
            if "input" in obj_type.lower():
                _cls = BAC0.local.multiStateInput.create_MSI
            elif "output" in obj_type.lower():
                _cls = BAC0.local.multiStateOutput.create_MSO
            _cls(
                instance=config["instance"],
                name=config["name"],
                description=config.get("description", ""),
                presentValue=int(pv) if not isinstance(pv, bool) else 1,
                is_commandable=("output" in obj_type.lower() or "value" in obj_type.lower()),
            )

    async def stop_device(self, device_id: int) -> None:
        instance = self._instances.pop(device_id, None)
        if instance:
            loop = asyncio.get_event_loop()
            try:
                await loop.run_in_executor(None, instance.disconnect)
            except Exception as e:
                logger.warning("Error stopping device %d: %s", device_id, e)
            self._devices.pop(device_id, None)
            logger.info("Stopped BACnet device %d", device_id)

    async def stop_all(self) -> None:
        device_ids = list(self._instances.keys())
        for device_id in device_ids:
            await self.stop_device(device_id)

    async def write_point_value(
        self, device_id: int, object_type: PointType, instance: int, value: PointValue
    ) -> None:
        bac0_instance = self._instances.get(device_id)
        if not bac0_instance:
            raise ValueError(f"Device {device_id} not running")
        device = self._devices.get(device_id)
        if not device:
            raise ValueError(f"Device {device_id} not found")
        point = device.get_point(object_type, instance)
        if not point:
            raise ValueError(
                f"Point {object_type}:{instance} not found on device {device_id}"
            )
        point.present_value = value

    async def read_point_value(
        self, device_id: int, object_type: PointType, instance: int
    ) -> PointValue:
        device = self._devices.get(device_id)
        if not device:
            raise ValueError(f"Device {device_id} not found")
        point = device.get_point(object_type, instance)
        if not point:
            raise ValueError(
                f"Point {object_type}:{instance} not found on device {device_id}"
            )
        return point.present_value
