from __future__ import annotations

import asyncio
import socket
from dataclasses import dataclass

from bacpypes3.app import Application
from bacpypes3.pdu import IPv4Address
from bacpypes3.primitivedata import Null, ObjectIdentifier

from bacnet_lab.adapters.bacnet.object_builder import build_local_object
from bacnet_lab.adapters.bacnet.profile import (
    SimulatorApplication,
    SimulatorDeviceObject,
    SimulatorNetworkPortObject,
)
from bacnet_lab.domain.enums import PointType
from bacnet_lab.domain.errors import NotFoundError, UnavailableError
from bacnet_lab.domain.models.device import Device
from bacnet_lab.domain.value_objects import DeviceAddress, PointValue
from bacnet_lab.ports.device_network import DeviceNetworkPort


@dataclass
class Runtime:
    objects: dict[str, object]
    app: Application | None = None


class BACnetEngine(DeviceNetworkPort):
    """One independent protocol application per device.

    The small transport readiness/cleanup shim below is specific to BACpypes3
    0.0.106: its public close() does not cancel pending socket creation tasks.
    Keep that compatibility code here and cover it with network lifecycle tests.
    """

    def __init__(self, ip: str = "127.0.0.1", prefix: int = 32) -> None:
        self._ip = ip
        self._prefix = prefix
        self._runtimes: dict[int, Runtime] = {}

    async def start_device(self, device: Device, udp_port: int) -> None:
        runtime = self._runtimes.get(device.device_id)
        if runtime and runtime.app:
            return
        address = device.address or DeviceAddress(self._ip, udp_port)
        # BACpypes enables SO_REUSEPORT. Detect an occupied unicast address first
        # rather than accidentally sharing traffic with another application.
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.bind((address.ip, address.port))
        if runtime is None:
            runtime = Runtime({p.object_name: build_local_object(p) for p in device.points})
            self._runtimes[device.device_id] = runtime
        app = SimulatorApplication.from_object_list(
            [
                SimulatorDeviceObject(
                    objectIdentifier=("device", device.device_id),
                    objectName=device.name,
                    vendorIdentifier=999,
                    vendorName="BACnet Lab",
                    modelName="HVAC simulator",
                    description=device.description,
                ),
            ]
        )
        runtime.app = app
        try:
            for obj in runtime.objects.values():
                app.add_object(obj)
            app.add_object(
                SimulatorNetworkPortObject(
                    IPv4Address(f"{address.ip}/{self._prefix}:{address.port}"),
                    objectIdentifier=("networkPort", 1),
                    objectName="NetworkPort-1",
                )
            )
            tasks = [
                task for link in app.link_layers.values() for task in link.server._transport_tasks
            ]
            async with asyncio.timeout(5):
                await asyncio.gather(*tasks)
                # The transport completion callbacks run on the next loop turn.
                await asyncio.sleep(0)
            device.address = address
        except BaseException:
            await self.stop_device(device.device_id)
            raise

    async def stop_device(self, device_id: int) -> None:
        runtime = self._runtimes.get(device_id)
        if not runtime or not runtime.app:
            return
        app, runtime.app = runtime.app, None
        # Cancel COV timers so a retired application cannot keep notifying clients.
        for detection in list(app._cov_detections.values()):
            for subscription in list(detection.cov_subscriptions):
                app.cancel_subscription(subscription)
        tasks = [task for link in app.link_layers.values() for task in link.server._transport_tasks]
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        app.close()
        await asyncio.sleep(0)

    async def stop_all(self) -> None:
        errors = []
        for device_id in list(self._runtimes):
            try:
                await self.stop_device(device_id)
            except Exception as exc:
                errors.append(exc)
        self._runtimes.clear()
        if errors:
            raise ExceptionGroup("BACnet shutdown failed", errors)

    def _object(self, device_id: int, object_type: PointType, instance: int):
        runtime = self._runtimes.get(device_id)
        if not runtime or not runtime.app:
            raise UnavailableError(f"Device {device_id} is offline")
        obj = runtime.app.get_object_id(ObjectIdentifier((object_type.value, instance)))
        if obj is None:
            raise NotFoundError(f"Point {object_type}:{instance} not found")
        return obj

    async def write_point_value(
        self,
        device_id: int,
        object_type: PointType,
        instance: int,
        value: PointValue | None,
        priority: int = 16,
    ) -> int:
        obj = self._object(device_id, object_type, instance)
        if value is not None:
            value = obj._point.validate_value(value)
        if hasattr(obj, "priorityArray") and obj.priorityArray is not None:
            datatype = obj.get_property_type("presentValue")
            raw = (
                ("active" if value else "inactive")
                if object_type.value.startswith("binary")
                else value
            )
            await obj.write_property(
                "presentValue", Null(()) if value is None else datatype(raw), priority=priority
            )
            return obj._write_revisions[priority]
        else:
            if value is None:
                raise ValueError("Only commandable points can be relinquished")
            obj.update_sensor(
                ("active" if value else "inactive")
                if object_type.value.startswith("binary")
                else value
            )
            return obj._sensor_revision

    async def read_point_value(
        self, device_id: int, object_type: PointType, instance: int
    ) -> PointValue:
        value = self._object(device_id, object_type, instance).presentValue
        if object_type.value.startswith("binary"):
            return int(value) == 1
        if object_type.value.startswith("multiState"):
            return int(value)
        return float(value)

    async def read_priority_value(
        self, device_id: int, object_type: PointType, instance: int, priority: int
    ) -> PointValue | None:
        slot = self._object(device_id, object_type, instance).priorityArray[priority - 1]
        if slot._choice == "null":
            return None
        value = getattr(slot, slot._choice)
        if object_type.value.startswith("binary"):
            return int(value) == 1
        if object_type.value.startswith("multiState"):
            return int(value)
        return float(value)

    async def read_control_state(
        self, device_id: int, object_type: PointType, instance: int, priority: int
    ) -> tuple[PointValue | None, int]:
        obj = self._object(device_id, object_type, instance)
        if obj._point.commandable:
            value = await self.read_priority_value(device_id, object_type, instance, priority)
            return value, obj._write_revisions.get(priority, 0)
        value = obj._sensor_value
        if object_type.value.startswith("binary"):
            value = bool(int(obj.get_property_type("presentValue")(value)))
        elif object_type.value.startswith("multiState"):
            value = int(value)
        else:
            value = float(value)
        return value, obj._sensor_revision
