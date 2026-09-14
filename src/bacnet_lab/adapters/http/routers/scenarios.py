from dataclasses import asdict

from fastapi import APIRouter, Request

from bacnet_lab.adapters.http.dependencies import get_container
from bacnet_lab.adapters.http.schemas import ScenarioResponse, StartScenarioRequest

router = APIRouter(prefix="/api/scenarios", tags=["scenarios"])


@router.get("", response_model=list[ScenarioResponse])
async def list_scenarios(request: Request):
    return [asdict(s) for s in get_container(request).scenario_service.list_scenarios()]


@router.post("/{scenario_id}/start", response_model=ScenarioResponse)
async def start_scenario(
    request: Request, scenario_id: str, req: StartScenarioRequest | None = None
):
    return asdict(
        await get_container(request).scenario_service.start_scenario(
            scenario_id, req.params if req else None
        )
    )


@router.post("/{scenario_id}/stop", response_model=ScenarioResponse)
async def stop_scenario(request: Request, scenario_id: str):
    return asdict(await get_container(request).scenario_service.stop_scenario(scenario_id))
