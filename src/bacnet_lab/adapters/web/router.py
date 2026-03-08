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
    container = get_container()
    devices = container.device_service.get_all_in_memory_devices()
    scenarios = container.scenario_service.list_scenarios()
    active_scenarios = sum(1 for s in scenarios if s.status == ScenarioStatus.RUNNING)
    active_alarms = await container.alarm_repo.get_active()
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "devices": devices,
            "scenarios_count": len(scenarios),
            "active_scenarios": active_scenarios,
            "alarm_count": len(active_alarms),
        },
    )


@router.get("/devices", response_class=HTMLResponse)
async def devices_page(request: Request) -> HTMLResponse:
    container = get_container()
    devices = await container.device_service.list_devices()
    return templates.TemplateResponse(
        "devices.html", {"request": request, "devices": devices}
    )


@router.get("/devices/{device_id}", response_class=HTMLResponse)
async def device_detail(request: Request, device_id: int) -> HTMLResponse:
    container = get_container()
    device = await container.device_service.get_device(device_id)
    if not device:
        return HTMLResponse(content="Device not found", status_code=404)
    return templates.TemplateResponse(
        "device_detail.html", {"request": request, "device": device}
    )


@router.get("/scenarios", response_class=HTMLResponse)
async def scenarios_page(request: Request) -> HTMLResponse:
    container = get_container()
    scenarios = container.scenario_service.list_scenarios()
    return templates.TemplateResponse(
        "scenarios.html", {"request": request, "scenarios": scenarios}
    )


@router.get("/endpoints", response_class=HTMLResponse)
async def endpoints_page(request: Request) -> HTMLResponse:
    container = get_container()
    endpoints = await container.endpoint_service.list_endpoints()
    return templates.TemplateResponse(
        "endpoints.html", {"request": request, "endpoints": endpoints}
    )


@router.get("/events", response_class=HTMLResponse)
async def events_page(request: Request) -> HTMLResponse:
    container = get_container()
    events = await container.event_service.list_recent_events(100)
    alarms = await container.alarm_repo.list_recent(50)
    return templates.TemplateResponse(
        "events.html", {"request": request, "events": events, "alarms": alarms}
    )


# HTMX partials

@router.get("/partials/device-cards", response_class=HTMLResponse)
async def partial_device_cards(request: Request) -> HTMLResponse:
    container = get_container()
    devices = container.device_service.get_all_in_memory_devices()
    return templates.TemplateResponse(
        "partials/device_card.html", {"request": request, "devices": devices}
    )


@router.get("/partials/points/{device_id}", response_class=HTMLResponse)
async def partial_point_rows(request: Request, device_id: int) -> HTMLResponse:
    container = get_container()
    device = container.device_service.get_in_memory_device(device_id)
    if not device:
        return HTMLResponse(content="", status_code=404)
    return templates.TemplateResponse(
        "partials/point_row.html", {"request": request, "device": device}
    )


@router.get("/partials/scenarios", response_class=HTMLResponse)
async def partial_scenario_cards(request: Request) -> HTMLResponse:
    container = get_container()
    scenarios = container.scenario_service.list_scenarios()
    return templates.TemplateResponse(
        "partials/scenario_card.html", {"request": request, "scenarios": scenarios}
    )


@router.get("/partials/events", response_class=HTMLResponse)
async def partial_event_rows(request: Request) -> HTMLResponse:
    container = get_container()
    events = await container.event_service.list_recent_events(50)
    return templates.TemplateResponse(
        "partials/event_row.html", {"request": request, "events": events}
    )
