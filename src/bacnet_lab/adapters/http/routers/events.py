from __future__ import annotations

from fastapi import APIRouter, Query, Request

from bacnet_lab.adapters.http.dependencies import get_container
from bacnet_lab.adapters.http.schemas import AlarmResponse, EventResponse

router = APIRouter(tags=["events"])


@router.get("/api/events", response_model=list[EventResponse])
async def list_events(
    request: Request, limit: int = Query(default=50, ge=1, le=500)
) -> list[EventResponse]:
    container = get_container(request)
    events = await container.event_service.list_recent_events(limit)
    return [
        EventResponse(
            id=e.id,
            event_type=e.event_type.value,
            timestamp=e.timestamp.isoformat(),
            payload=e.payload,
            delivered=e.delivered,
        )
        for e in events
    ]


@router.get("/api/alarms", response_model=list[AlarmResponse])
async def list_alarms(
    request: Request, active_only: bool = False, limit: int = Query(default=50, ge=1, le=500)
) -> list[AlarmResponse]:
    container = get_container(request)
    if active_only:
        alarms = await container.alarm_repo.get_active()
    else:
        alarms = await container.alarm_repo.list_recent(limit)
    return [
        AlarmResponse(
            id=a.id,
            device_id=a.device_id,
            point_name=a.point_name,
            severity=a.severity.value,
            message=a.message,
            raised_at=a.raised_at.isoformat(),
            cleared_at=a.cleared_at.isoformat() if a.cleared_at else None,
        )
        for a in alarms
    ]


@router.get("/api/deliveries")
async def list_deliveries(request: Request, limit: int = Query(default=100, ge=1, le=500)):
    return await get_container(request).event_service.delivery_history(limit)
