from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from bacnet_lab.adapters.http.dependencies import get_container
from bacnet_lab.domain.enums import ScenarioStatus

router = APIRouter(prefix="/ui", tags=["web"])

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    container = get_container(request)
    devices = await container.device_service.list_devices()
    scenarios = container.scenario_service.list_scenarios()
    active_scenarios = sum(1 for s in scenarios if s.status == ScenarioStatus.RUNNING)
    active_alarms = await container.alarm_repo.get_active()
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "devices": devices,
            "online_count": sum(d.status.value == "online" for d in devices),
            "scenarios_count": len(scenarios),
            "active_scenarios": active_scenarios,
            "alarm_count": len(active_alarms),
        },
    )


@router.get("/devices", response_class=HTMLResponse)
async def devices_page(request: Request) -> HTMLResponse:
    container = get_container(request)
    devices = await container.device_service.list_devices()
    return templates.TemplateResponse(
        request=request, name="devices.html", context={"devices": devices}
    )


@router.get("/devices/{device_id}", response_class=HTMLResponse)
async def device_detail(request: Request, device_id: int) -> HTMLResponse:
    container = get_container(request)
    device = await container.device_service.get_device(device_id)
    if not device:
        return HTMLResponse(content="Device not found", status_code=404)
    return templates.TemplateResponse(
        request=request, name="device_detail.html", context={"device": device}
    )


@router.get("/scenarios", response_class=HTMLResponse)
async def scenarios_page(request: Request) -> HTMLResponse:
    container = get_container(request)
    scenarios = container.scenario_service.list_scenarios()
    return templates.TemplateResponse(
        request=request, name="scenarios.html", context={"scenarios": scenarios}
    )


@router.get("/endpoints", response_class=HTMLResponse)
async def endpoints_page(request: Request) -> HTMLResponse:
    container = get_container(request)
    endpoints = await container.endpoint_service.list_endpoints()
    return templates.TemplateResponse(
        request=request, name="endpoints.html", context={"endpoints": endpoints}
    )


@router.get("/events", response_class=HTMLResponse)
async def events_page(request: Request) -> HTMLResponse:
    container = get_container(request)
    events = await container.event_service.list_recent_events(100)
    alarms = await container.alarm_repo.list_recent(50)
    return templates.TemplateResponse(
        request=request, name="events.html", context={"events": events, "alarms": alarms}
    )


# HTMX partials


@router.get("/partials/device-cards", response_class=HTMLResponse)
async def partial_device_cards(request: Request) -> HTMLResponse:
    container = get_container(request)
    devices = await container.device_service.list_devices()
    return templates.TemplateResponse(
        request=request, name="partials/device_card.html", context={"devices": devices}
    )


@router.get("/partials/points/{device_id}", response_class=HTMLResponse)
async def partial_point_rows(request: Request, device_id: int) -> HTMLResponse:
    container = get_container(request)
    device = await container.device_service.get_device(device_id)
    if not device:
        return HTMLResponse(content="", status_code=404)
    return templates.TemplateResponse(
        request=request, name="partials/point_row.html", context={"device": device}
    )


@router.get("/partials/scenarios", response_class=HTMLResponse)
async def partial_scenario_cards(request: Request) -> HTMLResponse:
    container = get_container(request)
    scenarios = container.scenario_service.list_scenarios()
    return templates.TemplateResponse(
        request=request, name="partials/scenario_card.html", context={"scenarios": scenarios}
    )


@router.get("/partials/events", response_class=HTMLResponse)
async def partial_event_rows(request: Request) -> HTMLResponse:
    container = get_container(request)
    events = await container.event_service.list_recent_events(50)
    return templates.TemplateResponse(
        request=request, name="partials/event_row.html", context={"events": events}
    )


@router.get("/partials/endpoints", response_class=HTMLResponse)
async def partial_endpoints(request: Request) -> HTMLResponse:
    endpoints = await get_container(request).endpoint_service.list_endpoints()
    return templates.TemplateResponse(
        request=request, name="partials/endpoint_cards.html", context={"endpoints": endpoints}
    )


@router.get("/partials/summary", response_class=HTMLResponse)
async def partial_summary(request: Request) -> HTMLResponse:
    c = get_container(request)
    devices = await c.device_service.list_devices()
    scenarios = c.scenario_service.list_scenarios()
    return templates.TemplateResponse(
        request=request,
        name="partials/summary.html",
        context={
            "devices": devices,
            "online_count": sum(d.status.value == "online" for d in devices),
            "scenarios_count": len(scenarios),
            "active_scenarios": sum(s.status.value == "running" for s in scenarios),
            "alarm_count": len(await c.alarm_repo.get_active()),
        },
    )


@router.get("/partials/alarms", response_class=HTMLResponse)
async def partial_alarms(request: Request) -> HTMLResponse:
    alarms = await get_container(request).alarm_repo.list_recent(50)
    return templates.TemplateResponse(
        request=request, name="partials/alarms.html", context={"alarms": alarms}
    )
