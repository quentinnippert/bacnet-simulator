from __future__ import annotations

import logging
import secrets
import uuid
from datetime import datetime, timezone

from bacnet_lab.domain.enums import EventType
from bacnet_lab.domain.models.endpoint import OutboundEndpoint
from bacnet_lab.domain.models.event import ReplicationEvent
from bacnet_lab.ports.event_delivery import EventDeliveryPort
from bacnet_lab.ports.repositories import EndpointRepositoryPort

logger = logging.getLogger(__name__)


class EndpointService:
    def __init__(
        self,
        repo: EndpointRepositoryPort,
        delivery: EventDeliveryPort,
    ) -> None:
        self._repo = repo
        self._delivery = delivery

    async def create_endpoint(
        self, url: str, event_types: list[EventType] | None = None
    ) -> OutboundEndpoint:
        endpoint = OutboundEndpoint(
            id=str(uuid.uuid4()),
            url=url,
            secret=secrets.token_hex(32),
            enabled=True,
            event_types=event_types or list(EventType),
            created_at=datetime.now(timezone.utc),
        )
        await self._repo.save(endpoint)
        logger.info("Created endpoint %s → %s", endpoint.id[:8], url)
        return endpoint

    async def list_endpoints(self) -> list[OutboundEndpoint]:
        return await self._repo.list_all()

    async def get_endpoint(self, endpoint_id: str) -> OutboundEndpoint | None:
        return await self._repo.get(endpoint_id)

    async def delete_endpoint(self, endpoint_id: str) -> None:
        await self._repo.delete(endpoint_id)
        logger.info("Deleted endpoint %s", endpoint_id[:8])

    async def toggle_endpoint(self, endpoint_id: str, enabled: bool) -> None:
        endpoint = await self._repo.get(endpoint_id)
        if endpoint:
            endpoint.enabled = enabled
            await self._repo.save(endpoint)

    async def test_endpoint(self, endpoint_id: str) -> bool:
        endpoint = await self._repo.get(endpoint_id)
        if not endpoint:
            return False
        test_event = ReplicationEvent(
            id=str(uuid.uuid4()),
            event_type=EventType.TELEMETRY_SNAPSHOT,
            timestamp=datetime.now(timezone.utc),
            payload={"test": True, "message": "Test delivery from BACnet Lab"},
        )
        success = await self._delivery.deliver(test_event, endpoint)
        await self._repo.update_delivery_status(endpoint_id, success)
        return success
