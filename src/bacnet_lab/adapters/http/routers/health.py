from fastapi import APIRouter, Request, Response

from bacnet_lab import __version__
from bacnet_lab.adapters.http.dependencies import get_container
from bacnet_lab.adapters.http.schemas import HealthResponse
from bacnet_lab.domain.enums import DeviceStatus, ScenarioStatus

router = APIRouter(tags=["health"])


@router.get("/api/health", response_model=HealthResponse)
async def health(request: Request, response: Response):
    container = get_container(request)
    devices = container.device_service.get_all_in_memory_devices()
    scenarios = container.scenario_service.list_scenarios()
    errors = [
        f"Device {d.device_id}: {d.error or d.status.value}"
        for d in devices
        if d.status == DeviceStatus.ERROR
    ]
    errors += [f"Scenario {s.id}: {s.error}" for s in scenarios if s.status == ScenarioStatus.ERROR]
    errors += [
        service.error
        for service in (container.telemetry_service, container.event_service)
        if service.error
    ]
    try:
        await container.event_service.check()
    except Exception:
        errors.append("Database unavailable")
    if not devices:
        errors.append("No devices configured")
    if errors:
        response.status_code = 503
    return HealthResponse(
        status="degraded" if errors else "ok",
        version=__version__,
        devices_count=len(devices),
        online_devices=sum(d.status == DeviceStatus.ONLINE for d in devices),
        active_scenarios=sum(s.status == ScenarioStatus.RUNNING for s in scenarios),
        errors=errors,
    )
