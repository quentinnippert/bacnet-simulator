from __future__ import annotations

import logging

from bacnet_lab.adapters.scenarios.base import BaseScenario
from bacnet_lab.domain.models.scenario import Scenario
from bacnet_lab.ports.scenario_runner import ScenarioRunnerPort

logger = logging.getLogger(__name__)


class ScenarioRegistry(ScenarioRunnerPort):
    def __init__(self) -> None:
        self._scenarios: dict[str, BaseScenario] = {}

    def register(self, scenario: BaseScenario) -> None:
        self._scenarios[scenario.id] = scenario
        logger.info("Registered scenario: %s", scenario.id)

    async def start(self, scenario_id: str, params: dict | None = None) -> Scenario:
        scenario = self._scenarios.get(scenario_id)
        if not scenario:
            raise ValueError(f"Unknown scenario: {scenario_id}")
        await scenario.start(params)
        return scenario.to_domain()

    async def stop(self, scenario_id: str) -> Scenario:
        scenario = self._scenarios.get(scenario_id)
        if not scenario:
            raise ValueError(f"Unknown scenario: {scenario_id}")
        await scenario.stop()
        return scenario.to_domain()

    def list_scenarios(self) -> list[Scenario]:
        return [s.to_domain() for s in self._scenarios.values()]

    def get_scenario(self, scenario_id: str) -> Scenario | None:
        s = self._scenarios.get(scenario_id)
        return s.to_domain() if s else None
