from __future__ import annotations

import logging
import secrets
import uuid
from datetime import UTC, datetime

from bacnet_lab.application.webhook_policy import validate_webhook_url
from bacnet_lab.domain.enums import EventType
from bacnet_lab.domain.errors import NotFoundError
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
        allowed_hosts: list[str] | None = None,
    ) -> None:
        self._repo = repo
        self._delivery = delivery
        self._allowed_hosts = {
            host.lower()
            for host in (["localhost", "127.0.0.1"] if allowed_hosts is None else allowed_hosts)
        }

    async def create_endpoint(
        self, url: str, event_types: list[EventType] | None = None
    ) -> OutboundEndpoint:
        self.validate_url(url)
        endpoint = OutboundEndpoint(
            id=str(uuid.uuid4()),
            url=url,
            secret=secrets.token_hex(32),
            enabled=True,
            event_types=event_types or list(EventType),
            created_at=datetime.now(UTC),
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
            raise NotFoundError("Endpoint not found")
        test_event = ReplicationEvent(
            id=str(uuid.uuid4()),
            event_type=EventType.TELEMETRY_SNAPSHOT,
            timestamp=datetime.now(UTC),
            payload={"test": True, "message": "Test delivery from BACnet Lab"},
        )
        success = await self._delivery.deliver(test_event, endpoint)
        await self._repo.update_delivery_status(endpoint_id, success)
        return success

    def validate_url(self, url: str) -> None:
        validate_webhook_url(url, self._allowed_hosts)

    async def close(self) -> None:
        await self._delivery.close()
