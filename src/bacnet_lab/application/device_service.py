from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from copy import deepcopy

from bacnet_lab.domain.enums import DeviceStatus, PointType
from bacnet_lab.domain.errors import ConflictError, NotFoundError, UnavailableError, ValidationError
from bacnet_lab.domain.events import DeviceStatusChanged, PointValueChanged
from bacnet_lab.domain.models.device import Device, Point
from bacnet_lab.domain.value_objects import DeviceAddress, PointValue
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
        bacnet_ip: str = "127.0.0.1",
    ) -> None:
        self._repo, self._network, self._events = device_repo, network, event_publisher
        self._port_start = bacnet_port_start
        self._ip = bacnet_ip
        self._devices: dict[int, Device] = {}
        self._ports: dict[int, int] = {}
        self._locks: dict[int, asyncio.Lock] = {}
        self._owners: dict[tuple[int, str], str] = {}

    async def initialize_devices(self, devices: list[Device]) -> None:
        if self._port_start + len(devices) - 1 > 65535:
            raise ValidationError("Device ports exceed 65535")
        addresses = [
            d.address or DeviceAddress(self._ip, self._port_start + i)
            for i, d in enumerate(devices)
        ]
        if len(set(addresses)) != len(addresses):
            raise ValidationError("Two devices would bind the same IP and UDP port")
        for device, address in zip(devices, addresses):
            device.address = address
        for i, device in enumerate(devices):
            self._ports[device.device_id] = (
                device.address.port if device.address else self._port_start + i
            )
            self._locks[device.device_id] = asyncio.Lock()
            self._devices[device.device_id] = device
            try:
                await self._network.start_device(device, self._ports[device.device_id])
            except Exception as exc:
                logger.exception("Failed to start device %s", device.name)
                device.status, device.error = DeviceStatus.ERROR, str(exc)
            await self._repo.save(device)
        await self._repo.reconcile(set(self._devices))

    def _device(self, device_id: int) -> Device:
        if device_id not in self._devices:
            raise NotFoundError(f"Device {device_id} not found")
        return self._devices[device_id]

    def point(self, device_id: int, name: str) -> Point:
        point = self._device(device_id).get_point_by_name(name)
        if point is None:
            raise NotFoundError(f"Point {name!r} not found on device {device_id}")
        return deepcopy(point)

    async def _refresh(self, device: Device) -> None:
        if device.status != DeviceStatus.ONLINE:
            return
        for point in device.points:
            value = await self._network.read_point_value(
                device.device_id, point.object_type, point.object_instance
            )
            if value == point.present_value:
                continue
            # Keep the old in-memory value until both persistence and event recording
            # succeed. A failed recording will be retried on the next synchronization.
            await self._repo.update_point_value(device.device_id, point.object_name, value)
            await self._events.publish(
                PointValueChanged(
                    device_id=device.device_id,
                    point_name=point.object_name,
                    old_value=point.present_value,
                    new_value=value,
                )
            )
            point.present_value = value

    async def synchronize(self) -> None:
        for device in self._devices.values():
            async with self._locks[device.device_id]:
                await self._refresh(device)

    async def list_devices(self) -> list[Device]:
        await self.synchronize()
        return deepcopy(list(self._devices.values()))

    async def get_device(self, device_id: int) -> Device | None:
        device = self._devices.get(device_id)
        if device is None:
            return None
        async with self._locks[device_id]:
            await self._refresh(device)
            return deepcopy(device)

    async def write_point(
        self,
        device_id: int,
        object_type: PointType,
        instance: int,
        value: PointValue | None,
        priority: int = 16,
        owner: str | None = None,
    ) -> Point:
        device = self._device(device_id)
        point = device.get_point(object_type, instance)
        if point is None:
            raise NotFoundError(f"Point {object_type}:{instance} not found")
        if type(priority) is not int or not 1 <= priority <= 16 or priority == 6:
            raise ValidationError("Priority must be 1..16, excluding reserved priority 6")
        if value is None and not point.commandable:
            raise ValidationError("Only commandable points can be relinquished")
        value = point.validate_value(value) if value is not None else None
        async with self._locks[device_id]:
            if device.status != DeviceStatus.ONLINE:
                raise UnavailableError(f"Device {device_id} is {device.status.value}")
            held_by = self._owners.get((device_id, point.object_name))
            if held_by and held_by != owner:
                if owner is not None:  # Background simulation yields to an explicit override.
                    await self._refresh(device)
                    return deepcopy(point)
                raise ConflictError(f"Point is controlled by scenario {held_by}")
            await self._network.write_point_value(device_id, object_type, instance, value, priority)
            await self._refresh(device)
            return deepcopy(point)

    async def write_point_by_name(
        self,
        device_id: int,
        point_name: str,
        value: PointValue | None,
        priority: int = 16,
        owner: str | None = None,
    ) -> Point:
        point = self.point(device_id, point_name)
        return await self.write_point(
            device_id, point.object_type, point.object_instance, value, priority, owner
        )

    @asynccontextmanager
    async def override(self, device_id: int, point_name: str, value: PointValue, owner: str):
        device = self._device(device_id)
        point = self.point(device_id, point_name)
        value = point.validate_value(value)
        key = (device_id, point_name)
        revision = None
        async with self._locks[device_id]:
            if device.status != DeviceStatus.ONLINE:
                raise UnavailableError(f"Device {device_id} is not online")
            if key in self._owners:
                raise ConflictError(f"Point already controlled by {self._owners[key]}")
            previous, _ = await self._network.read_control_state(
                device_id, point.object_type, point.object_instance, 8
            )
            self._owners[key] = owner
        try:
            async with self._locks[device_id]:
                revision = await self._network.write_point_value(
                    device_id, point.object_type, point.object_instance, value, 8
                )
                await self._refresh(device)
            yield
        finally:
            try:
                if revision is not None:
                    async with self._locks[device_id]:
                        _, current_revision = await self._network.read_control_state(
                            device_id, point.object_type, point.object_instance, 8
                        )
                        # A later same-value command also belongs to its new writer.
                        if current_revision == revision:
                            await self._network.write_point_value(
                                device_id, point.object_type, point.object_instance, previous, 8
                            )
                            await self._refresh(device)
            finally:
                self._owners.pop(key, None)

    async def set_device_status(self, device_id: int, status: DeviceStatus) -> None:
        device = self._device(device_id)
        if status not in (DeviceStatus.ONLINE, DeviceStatus.OFFLINE):
            raise ValidationError("Only online/offline transitions can be requested")
        async with self._locks[device_id]:
            if status == device.status:
                return
            if any(key[0] == device_id for key in self._owners):
                raise ConflictError("Stop point overrides before taking the device offline")
            old_status = device.status
            try:
                if status == DeviceStatus.OFFLINE:
                    await self._refresh(device)
                    await self._network.stop_device(device_id)
                else:
                    await self._network.start_device(device, self._ports[device_id])
                device.status, device.error = status, None
            except Exception as exc:
                device.status, device.error = DeviceStatus.ERROR, str(exc)
                await self._repo.update_status(device_id, device.status.value)
                raise UnavailableError(f"Device transition failed: {exc}") from exc
            await self._repo.update_status(device_id, status.value)
            await self._events.publish(
                DeviceStatusChanged(device_id=device_id, old_status=old_status, new_status=status)
            )

    def get_in_memory_device(self, device_id: int) -> Device | None:
        return deepcopy(self._devices.get(device_id))

    def get_all_in_memory_devices(self) -> list[Device]:
        return deepcopy(list(self._devices.values()))

    async def shutdown(self) -> None:
        await self._network.stop_all()
