from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, Response

from bacnet_lab.adapters.http.dependencies import get_container
from bacnet_lab.adapters.http.schemas import (
    EndpointCreatedResponse,
    EndpointCreateRequest,
    EndpointResponse,
)

router = APIRouter(prefix="/api/endpoints", tags=["endpoints"])


@router.get("", response_model=list[EndpointResponse])
async def list_endpoints(request: Request) -> list[EndpointResponse]:
    container = get_container(request)
    endpoints = await container.endpoint_service.list_endpoints()
    return [
        EndpointResponse(
            id=ep.id,
            url=ep.url,
            enabled=ep.enabled,
            event_types=[et.value for et in ep.event_types],
            failure_count=ep.failure_count,
        )
        for ep in endpoints
    ]


@router.post("", response_model=EndpointCreatedResponse, status_code=201)
async def create_endpoint(request: Request, req: EndpointCreateRequest) -> EndpointCreatedResponse:
    container = get_container(request)
    ep = await container.endpoint_service.create_endpoint(req.url, req.event_types)
    return EndpointCreatedResponse(
        id=ep.id,
        url=ep.url,
        secret=ep.secret,
        enabled=ep.enabled,
        event_types=[et.value for et in ep.event_types],
        failure_count=ep.failure_count,
    )


@router.delete("/{endpoint_id}", status_code=204, response_class=Response)
async def delete_endpoint(request: Request, endpoint_id: str) -> Response:
    container = get_container(request)
    await container.endpoint_service.delete_endpoint(endpoint_id)
    return Response(status_code=204)


@router.post("/{endpoint_id}/test")
async def test_endpoint(request: Request, endpoint_id: str) -> dict:
    container = get_container(request)
    success = await container.endpoint_service.test_endpoint(endpoint_id)
    if not success:
        raise HTTPException(status_code=502, detail="Delivery failed")
    return {"status": "ok"}
