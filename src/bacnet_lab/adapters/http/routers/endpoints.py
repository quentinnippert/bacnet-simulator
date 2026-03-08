from __future__ import annotations

from fastapi import APIRouter, HTTPException

from bacnet_lab.adapters.http.dependencies import get_container
from bacnet_lab.adapters.http.schemas import EndpointCreateRequest, EndpointResponse

router = APIRouter(prefix="/api/endpoints", tags=["endpoints"])


@router.get("", response_model=list[EndpointResponse])
async def list_endpoints() -> list[EndpointResponse]:
    container = get_container()
    endpoints = await container.endpoint_service.list_endpoints()
    return [
        EndpointResponse(
            id=ep.id,
            url=ep.url,
            secret=ep.secret,
            enabled=ep.enabled,
            event_types=[et.value for et in ep.event_types],
            failure_count=ep.failure_count,
        )
        for ep in endpoints
    ]


@router.post("", response_model=EndpointResponse, status_code=201)
async def create_endpoint(req: EndpointCreateRequest) -> EndpointResponse:
    container = get_container()
    ep = await container.endpoint_service.create_endpoint(req.url, req.event_types)
    return EndpointResponse(
        id=ep.id,
        url=ep.url,
        secret=ep.secret,
        enabled=ep.enabled,
        event_types=[et.value for et in ep.event_types],
        failure_count=ep.failure_count,
    )


@router.delete("/{endpoint_id}", status_code=204)
async def delete_endpoint(endpoint_id: str) -> None:
    container = get_container()
    await container.endpoint_service.delete_endpoint(endpoint_id)


@router.post("/{endpoint_id}/test")
async def test_endpoint(endpoint_id: str) -> dict:
    container = get_container()
    success = await container.endpoint_service.test_endpoint(endpoint_id)
    if not success:
        raise HTTPException(status_code=502, detail="Delivery failed")
    return {"status": "ok"}
