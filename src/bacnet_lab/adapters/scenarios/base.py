from __future__ import annotations

import asyncio
import logging
import math
from abc import ABC, abstractmethod

from bacnet_lab.application.device_service import DeviceService
from bacnet_lab.domain.enums import DeviceStatus, ScenarioStatus
from bacnet_lab.domain.errors import UnavailableError, ValidationError
from bacnet_lab.domain.events import ScenarioLifecycleChanged
from bacnet_lab.domain.models.scenario import Scenario, ScenarioParameter
from bacnet_lab.ports.event_publisher import EventPublisherPort

logger = logging.getLogger(__name__)


class BaseScenario(ABC):
    id: str
    name: str
    description: str

    def __init__(self, device_service: DeviceService, event_publisher: EventPublisherPort) -> None:
        self._device_service, self._event_publisher = device_service, event_publisher
        self._task: asyncio.Task | None = None
        self._status = ScenarioStatus.IDLE
        self._parameters = self.default_parameters()
        self._lock = asyncio.Lock()
        self.error: str | None = None

    def default_parameters(self) -> list[ScenarioParameter]:
        return []

    def parameter(self, name: str):
        return next(p.value for p in self._parameters if p.name == name)

    def validate(self) -> None:
        """Validate target requirements before reporting a successful start."""

    def require_point(self, device_id: int, point_name: str, value=None) -> None:
        point = self._device_service.point(device_id, point_name)
        device = self._device_service.get_in_memory_device(device_id)
        if device.status != DeviceStatus.ONLINE:
            raise UnavailableError(f"Device {device_id} is not online")
        if value is not None:
            point.validate_value(value)

    async def write(self, device_id: int, name: str, value) -> None:
        device = self._device_service.get_in_memory_device(device_id)
        if device and device.status == DeviceStatus.OFFLINE:
            return  # An explicitly offline device does not participate in a tick.
        await self._device_service.write_point_by_name(device_id, name, value, owner=self.id)

    @abstractmethod
    async def run(self) -> None: ...

    async def start(self, params: dict | None = None) -> None:
        async with self._lock:
            if self._task and not self._task.done():
                return
            parameters = self.default_parameters()
            params = params or {}
            unknown = set(params) - {p.name for p in parameters}
            if unknown:
                raise ValidationError(f"Unknown scenario parameters: {', '.join(sorted(unknown))}")
            for p in parameters:
                value = params.get(p.name, p.default)
                if p.name == "override_value":
                    pass  # Target point validates analog/binary/multistate types below.
                elif type(p.default) in (int, float):
                    if (
                        type(value) not in (int, float)
                        or not -1e308 <= value <= 1e308
                        or not math.isfinite(value)
                    ):
                        raise ValidationError(f"{p.name} must be a finite number")
                    if p.name == "device_id" and type(value) is not int:
                        raise ValidationError("device_id must be an integer")
                    if p.name.endswith(("duration", "seconds")) or p.name == "interval":
                        if value < 0.01 or value > 86400:
                            raise ValidationError(f"{p.name} must be between .01 and 86400 seconds")
                elif type(value) is not type(p.default):
                    raise ValidationError(f"Invalid type for {p.name}")
                p.current = value
            self._parameters = parameters
            self.validate()
            await self._event_publisher.publish(
                ScenarioLifecycleChanged(scenario_id=self.id, new_status=ScenarioStatus.RUNNING)
            )
            self._status, self.error = ScenarioStatus.RUNNING, None
            self._task = asyncio.create_task(self._run_wrapper(), name=f"scenario:{self.id}")

    async def stop(self) -> None:
        async with self._lock:
            if self._task and not self._task.done():
                self._task.cancel()
                try:
                    await self._task
                except asyncio.CancelledError:
                    # A task cancelled before its first turn never enters its finally.
                    self._status = ScenarioStatus.STOPPED
                    await self._event_publisher.publish(
                        ScenarioLifecycleChanged(scenario_id=self.id, new_status=self._status)
                    )
            self._task = None

    async def _run_wrapper(self) -> None:
        try:
            await self.run()
            self._status = ScenarioStatus.STOPPED
        except asyncio.CancelledError:
            self._status = ScenarioStatus.STOPPED
        except Exception as exc:
            self._status, self.error = ScenarioStatus.ERROR, str(exc)
            logger.exception("Scenario %s failed", self.id)
        finally:
            try:
                await self._event_publisher.publish(
                    ScenarioLifecycleChanged(
                        scenario_id=self.id, new_status=self._status, error=self.error
                    )
                )
            except Exception as exc:
                self._status, self.error = (
                    ScenarioStatus.ERROR,
                    f"Lifecycle recording failed: {exc}",
                )
                logger.exception("Could not record scenario %s completion", self.id)

    def to_domain(self) -> Scenario:
        return Scenario(
            id=self.id,
            name=self.name,
            description=self.description,
            status=self._status,
            parameters=list(self._parameters),
            error=self.error,
        )

    @property
    def is_running(self) -> bool:
        return self._status == ScenarioStatus.RUNNING
