from dataclasses import asdict

from fastapi import APIRouter, Request

from bacnet_lab.adapters.http.dependencies import get_container
from bacnet_lab.adapters.http.schemas import (
    DeviceDetailResponse,
    DeviceResponse,
    PointResponse,
    WritePointRequest,
)
from bacnet_lab.domain.errors import NotFoundError

router = APIRouter(prefix="/api/devices", tags=["devices"])


@router.get("", response_model=list[DeviceResponse])
async def list_devices(request: Request):
    devices = await get_container(request).device_service.list_devices()
    return [
        dict(
            device_id=d.device_id,
            name=d.name,
            description=d.description,
            status=d.status,
            point_count=len(d.points),
            address=str(d.address) if d.address else None,
            error=d.error,
        )
        for d in devices
    ]


@router.get("/{device_id}", response_model=DeviceDetailResponse)
async def get_device(request: Request, device_id: int):
    device = await get_container(request).device_service.get_device(device_id)
    if device is None:
        raise NotFoundError("Device not found")
    data = asdict(device)
    data["points"] = [PointResponse.model_validate(p) for p in device.points]
    return data


@router.put("/{device_id}/points", response_model=PointResponse)
async def write_point(request: Request, device_id: int, req: WritePointRequest):
    service = get_container(request).device_service
    if req.point_name is not None:
        point = await service.write_point_by_name(
            device_id, req.point_name, req.value, req.priority
        )
    else:
        point = await service.write_point(
            device_id, req.object_type, req.object_instance, req.value, req.priority
        )
    return PointResponse.model_validate(point)
