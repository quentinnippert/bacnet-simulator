from __future__ import annotations

import logging

from bacnet_lab.domain.enums import DeviceStatus, PointType
from bacnet_lab.domain.events import DeviceStatusChanged, PointValueChanged
from bacnet_lab.domain.models.device import Device
from bacnet_lab.domain.value_objects import PointValue
from bacnet_lab.ports.device_network import DeviceNetworkPort
from bacnet_lab.ports.event_publisher import EventPublisherPort
from bacnet_lab.ports.repositories import DeviceRepositoryPort

logger = logging.getLogger(__name__)


class DeviceService:
    def __init__(
        self,
        device_repo: DeviceRepositoryPort,
        network: DeviceNetworkPort,
        event_publisher: EventPublisherPort,
        bacnet_port_start: int = 47808,
    ) -> None:
        self._repo = device_repo
        self._network = network
        self._events = event_publisher
        self._port_start = bacnet_port_start
        self._devices: dict[int, Device] = {}

    async def initialize_devices(self, devices: list[Device]) -> None:
        for i, device in enumerate(devices):
            udp_port = self._port_start + i
            try:
                await self._network.start_device(device, udp_port)
                device.status = DeviceStatus.ONLINE
            except Exception as e:
                logger.error("Failed to start device %s: %s", device.name, e)
                device.status = DeviceStatus.ERROR
            await self._repo.save(device)
            self._devices[device.device_id] = device
            logger.info("Initialized device %s (ID=%d)", device.name, device.device_id)

    async def list_devices(self) -> list[Device]:
        return await self._repo.list_all()

    async def get_device(self, device_id: int) -> Device | None:
        return await self._repo.get(device_id)

    async def write_point(
        self,
        device_id: int,
        object_type: PointType,
        instance: int,
        value: PointValue,
    ) -> None:
        device = self._devices.get(device_id)
        if not device:
            raise ValueError(f"Device {device_id} not found")
        point = device.get_point(object_type, instance)
        if not point:
            raise ValueError(f"Point {object_type}:{instance} not found")
        old_value = point.present_value
        await self._network.write_point_value(device_id, object_type, instance, value)
        point.present_value = value
        await self._repo.update_point_value(device_id, point.object_name, value)
        await self._events.publish(
            PointValueChanged(
                device_id=device_id,
                point_name=point.object_name,
                old_value=old_value,
                new_value=value,
            )
        )

    async def write_point_by_name(
        self, device_id: int, point_name: str, value: PointValue
    ) -> None:
        device = self._devices.get(device_id)
        if not device:
            raise ValueError(f"Device {device_id} not found")
        point = device.get_point_by_name(point_name)
        if not point:
            raise ValueError(f"Point '{point_name}' not found on device {device_id}")
        await self.write_point(device_id, point.object_type, point.object_instance, value)

    async def set_device_status(self, device_id: int, status: DeviceStatus) -> None:
        device = self._devices.get(device_id)
        if not device:
            raise ValueError(f"Device {device_id} not found")
        old_status = device.status
        device.status = status
        await self._repo.update_status(device_id, status.value)
        await self._events.publish(
            DeviceStatusChanged(
                device_id=device_id,
                old_status=old_status,
                new_status=status,
            )
        )

    def get_in_memory_device(self, device_id: int) -> Device | None:
        return self._devices.get(device_id)

    def get_all_in_memory_devices(self) -> list[Device]:
        return list(self._devices.values())

    async def shutdown(self) -> None:
        await self._network.stop_all()
