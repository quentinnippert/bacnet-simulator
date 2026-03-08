from __future__ import annotations

import logging

from bacnet_lab.domain.models.scenario import Scenario
from bacnet_lab.ports.scenario_runner import ScenarioRunnerPort

logger = logging.getLogger(__name__)


class ScenarioService:
    def __init__(self, runner: ScenarioRunnerPort) -> None:
        self._runner = runner

    def list_scenarios(self) -> list[Scenario]:
        return self._runner.list_scenarios()

    def get_scenario(self, scenario_id: str) -> Scenario | None:
        return self._runner.get_scenario(scenario_id)

    async def start_scenario(self, scenario_id: str, params: dict | None = None) -> Scenario:
        logger.info("Starting scenario %s", scenario_id)
        return await self._runner.start(scenario_id, params)

    async def stop_scenario(self, scenario_id: str) -> Scenario:
        logger.info("Stopping scenario %s", scenario_id)
        return await self._runner.stop(scenario_id)
