from __future__ import annotations

import asyncio
import logging

from bacnet_lab.domain.enums import PointType
from bacnet_lab.domain.models.device import Device
from bacnet_lab.domain.value_objects import DeviceAddress, PointValue
from bacnet_lab.ports.device_network import DeviceNetworkPort

logger = logging.getLogger(__name__)


def _remove_invalid_fd_bbmd_address(instance: object) -> None:
    """Remove the malformed optional address BAC0 creates outside foreign mode."""
    try:
        application = instance.this_application.app
        network_port = application.get_object_name("NetworkPort-1")
    except AttributeError:
        return

    if network_port is None:
        return

    fd_bbmd_address = getattr(network_port, "fdBBMDAddress", None)
    if fd_bbmd_address is None or getattr(fd_bbmd_address, "host", None) is not None:
        return

    del network_port.fdBBMDAddress


class BAC0Engine(DeviceNetworkPort):
    """Manages one BAC0 lite instance per device on separate UDP ports.

    BAC0 2025.x (bacpypes3) is fully async — all calls to BAC0.lite() and
    object factory functions must happen within a running asyncio event loop.
    No run_in_executor: BAC0 internally uses asyncio.get_running_loop().
    """

    def __init__(self, ip: str = "0.0.0.0") -> None:
        self._ip = ip
        self._instances: dict[int, object] = {}  # device_id -> BAC0 Lite instance
        self._devices: dict[int, Device] = {}

    async def start_device(self, device: Device, udp_port: int) -> None:
        import BAC0
        from BAC0.core.devices.local.factory import ObjectFactory

        from bacnet_lab.adapters.bacnet.object_builder import build_local_object

        try:
            # BAC0.lite() is synchronous but requires a running event loop
            instance = BAC0.lite(
                ip=f"{self._ip}/24:{udp_port}",
                deviceId=device.device_id,
                localObjName=device.name,
            )

            # Wait for BAC0 async initialization to complete
            for _ in range(50):
                if getattr(instance, "_initialized", False):
                    break
                await asyncio.sleep(0.1)
            else:
                raise TimeoutError(
                    f"BAC0 instance for device {device.device_id} did not initialize within 5s"
                )

            _remove_invalid_fd_bbmd_address(instance)

            # Create local BACnet objects for each point
            for point in device.points:
                try:
                    factory = build_local_object(point)
                    factory.add_objects_to_application(instance)
                except Exception as e:
                    logger.warning(
                        "Failed to create object %s on device %d: %s",
                        point.object_name, device.device_id, e,
                    )

            # Clear the shared ObjectFactory state before the next device
            ObjectFactory.clear_objects()

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

    async def stop_device(self, device_id: int) -> None:
        instance = self._instances.pop(device_id, None)
        if instance:
            try:
                await instance._disconnect()
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

        # Update the BAC0 local object — let errors propagate so callers
        # don't update domain state with a value the device never received.
        try:
            bac0_obj = bac0_instance[point.object_name]
            bac0_obj.presentValue = value
        except (KeyError, AttributeError) as e:
            raise ValueError(
                f"Could not update BAC0 object {point.object_name}: {e}"
            ) from e

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
