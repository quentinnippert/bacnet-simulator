from __future__ import annotations

from fastapi import APIRouter

from bacnet_lab import __version__
from bacnet_lab.adapters.http.dependencies import get_container
from bacnet_lab.adapters.http.schemas import HealthResponse
from bacnet_lab.domain.enums import ScenarioStatus

router = APIRouter(tags=["health"])


@router.get("/api/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    container = get_container()
    devices = container.device_service.get_all_in_memory_devices()
    scenarios = container.scenario_service.list_scenarios()
    active = sum(1 for s in scenarios if s.status == ScenarioStatus.RUNNING)
    return HealthResponse(
        status="ok",
        version=__version__,
        devices_count=len(devices),
        active_scenarios=active,
    )
