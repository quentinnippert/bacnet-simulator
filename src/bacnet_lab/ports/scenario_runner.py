from __future__ import annotations

from abc import ABC, abstractmethod

from bacnet_lab.domain.models.scenario import Scenario


class ScenarioRunnerPort(ABC):
    @abstractmethod
    async def start(self, scenario_id: str, params: dict | None = None) -> Scenario: ...

    @abstractmethod
    async def stop(self, scenario_id: str) -> Scenario: ...

    @abstractmethod
    def list_scenarios(self) -> list[Scenario]: ...

    @abstractmethod
    def get_scenario(self, scenario_id: str) -> Scenario | None: ...
