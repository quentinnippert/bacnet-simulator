from __future__ import annotations

import logging
import uuid
from dataclasses import asdict

from bacnet_lab.domain.events import DomainEvent
from bacnet_lab.domain.models.event import ReplicationEvent
from bacnet_lab.ports.event_delivery import EventDeliveryPort
from bacnet_lab.ports.event_publisher import EventPublisherPort
from bacnet_lab.ports.repositories import EndpointRepositoryPort, EventLogRepositoryPort

logger = logging.getLogger(__name__)


class EventService:
    def __init__(
        self,
        event_publisher: EventPublisherPort,
        event_log_repo: EventLogRepositoryPort,
        endpoint_repo: EndpointRepositoryPort,
        delivery: EventDeliveryPort,
    ) -> None:
        self._event_publisher = event_publisher
        self._event_log_repo = event_log_repo
        self._endpoint_repo = endpoint_repo
        self._delivery = delivery
        self._event_publisher.subscribe(self._handle_domain_event)

    async def _handle_domain_event(self, event: DomainEvent) -> None:
        payload = {}
        for key, val in asdict(event).items():
            if key == "timestamp":
                payload[key] = val.isoformat() if hasattr(val, "isoformat") else str(val)
            elif key == "event_type":
                payload[key] = str(val)
            else:
                payload[key] = val

        replication_event = ReplicationEvent(
            id=str(uuid.uuid4()),
            event_type=event.event_type,
            timestamp=event.timestamp,
            payload=payload,
        )
        await self._event_log_repo.save(replication_event)
        await self._deliver_to_endpoints(replication_event)

    async def _deliver_to_endpoints(self, event: ReplicationEvent) -> None:
        endpoints = await self._endpoint_repo.list_all()
        for endpoint in endpoints:
            if not endpoint.enabled:
                continue
            if endpoint.event_types and event.event_type not in endpoint.event_types:
                continue
            try:
                success = await self._delivery.deliver(event, endpoint)
                await self._endpoint_repo.update_delivery_status(endpoint.id, success)
                if success:
                    await self._event_log_repo.mark_delivered(event.id)
            except Exception as e:
                logger.error(
                    "Failed to deliver event %s to %s: %s",
                    event.id[:8], endpoint.url, e,
                )

    async def list_recent_events(self, limit: int = 50) -> list[ReplicationEvent]:
        return await self._event_log_repo.list_recent(limit)
