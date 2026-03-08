from __future__ import annotations

from fastapi import APIRouter, HTTPException

from bacnet_lab.adapters.http.dependencies import get_container
from bacnet_lab.adapters.http.schemas import (
    DeviceDetailResponse,
    DeviceResponse,
    PointResponse,
    WritePointByNameRequest,
)

router = APIRouter(prefix="/api/devices", tags=["devices"])


@router.get("", response_model=list[DeviceResponse])
async def list_devices() -> list[DeviceResponse]:
    container = get_container()
    devices = await container.device_service.list_devices()
    return [
        DeviceResponse(
            device_id=d.device_id,
            name=d.name,
            description=d.description,
            status=d.status.value,
            point_count=len(d.points),
        )
        for d in devices
    ]


@router.get("/{device_id}", response_model=DeviceDetailResponse)
async def get_device(device_id: int) -> DeviceDetailResponse:
    container = get_container()
    device = await container.device_service.get_device(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return DeviceDetailResponse(
        device_id=device.device_id,
        name=device.name,
        description=device.description,
        status=device.status.value,
        points=[
            PointResponse(
                object_type=p.object_type.value,
                object_instance=p.object_instance,
                object_name=p.object_name,
                description=p.description,
                present_value=p.present_value,
                units=p.units,
            )
            for p in device.points
        ],
    )


@router.put("/{device_id}/points")
async def write_point(device_id: int, req: WritePointByNameRequest) -> dict:
    container = get_container()
    try:
        await container.device_service.write_point_by_name(device_id, req.point_name, req.value)
        return {"status": "ok"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
