from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod

from bacnet_lab.application.device_service import DeviceService
from bacnet_lab.domain.enums import ScenarioStatus
from bacnet_lab.domain.models.scenario import Scenario, ScenarioParameter
from bacnet_lab.ports.event_publisher import EventPublisherPort

logger = logging.getLogger(__name__)


class BaseScenario(ABC):
    id: str
    name: str
    description: str

    def __init__(
        self,
        device_service: DeviceService,
        event_publisher: EventPublisherPort,
    ) -> None:
        self._device_service = device_service
        self._event_publisher = event_publisher
        self._task: asyncio.Task | None = None
        self._status = ScenarioStatus.IDLE
        self._parameters: list[ScenarioParameter] = self.default_parameters()

    def default_parameters(self) -> list[ScenarioParameter]:
        return []

    @abstractmethod
    async def run(self) -> None:
        """Main scenario loop. Should check self._status periodically."""
        ...

    async def start(self, params: dict | None = None) -> None:
        if self._status == ScenarioStatus.RUNNING:
            return
        if params:
            for p in self._parameters:
                if p.name in params:
                    p.current = params[p.name]
        self._status = ScenarioStatus.RUNNING
        self._task = asyncio.create_task(self._run_wrapper())
        logger.info("Scenario %s started", self.id)

    async def stop(self) -> None:
        self._status = ScenarioStatus.STOPPED
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("Scenario %s stopped", self.id)

    async def _run_wrapper(self) -> None:
        try:
            await self.run()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error("Scenario %s error: %s", self.id, e)
            self._status = ScenarioStatus.ERROR
        finally:
            if self._status == ScenarioStatus.RUNNING:
                self._status = ScenarioStatus.STOPPED

    def to_domain(self) -> Scenario:
        return Scenario(
            id=self.id,
            name=self.name,
            description=self.description,
            status=self._status,
            parameters=list(self._parameters),
        )

    @property
    def is_running(self) -> bool:
        return self._status == ScenarioStatus.RUNNING
