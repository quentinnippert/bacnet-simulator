from __future__ import annotations

from fastapi import APIRouter, HTTPException

from bacnet_lab.adapters.http.dependencies import get_container
from bacnet_lab.adapters.http.schemas import ScenarioResponse, StartScenarioRequest

router = APIRouter(prefix="/api/scenarios", tags=["scenarios"])


@router.get("", response_model=list[ScenarioResponse])
async def list_scenarios() -> list[ScenarioResponse]:
    container = get_container()
    scenarios = container.scenario_service.list_scenarios()
    return [
        ScenarioResponse(
            id=s.id, name=s.name, description=s.description, status=s.status.value
        )
        for s in scenarios
    ]


@router.post("/{scenario_id}/start", response_model=ScenarioResponse)
async def start_scenario(scenario_id: str, req: StartScenarioRequest | None = None) -> ScenarioResponse:
    container = get_container()
    try:
        s = await container.scenario_service.start_scenario(
            scenario_id, req.params if req else None
        )
        return ScenarioResponse(
            id=s.id, name=s.name, description=s.description, status=s.status.value
        )
    except (ValueError, KeyError) as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{scenario_id}/stop", response_model=ScenarioResponse)
async def stop_scenario(scenario_id: str) -> ScenarioResponse:
    container = get_container()
    try:
        s = await container.scenario_service.stop_scenario(scenario_id)
        return ScenarioResponse(
            id=s.id, name=s.name, description=s.description, status=s.status.value
        )
    except (ValueError, KeyError) as e:
        raise HTTPException(status_code=404, detail=str(e))
