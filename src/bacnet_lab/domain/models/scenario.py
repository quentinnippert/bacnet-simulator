from __future__ import annotations

from dataclasses import dataclass, field

from bacnet_lab.domain.enums import ScenarioStatus


@dataclass
class ScenarioParameter:
    name: str
    description: str
    default: float | int | str | bool
    current: float | int | str | bool | None = None

    @property
    def value(self) -> float | int | str | bool:
        return self.current if self.current is not None else self.default


@dataclass
class Scenario:
    id: str
    name: str
    description: str
    status: ScenarioStatus = ScenarioStatus.IDLE
    parameters: list[ScenarioParameter] = field(default_factory=list)
