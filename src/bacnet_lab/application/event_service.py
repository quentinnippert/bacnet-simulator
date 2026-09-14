from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import asdict
from datetime import UTC, datetime, timedelta

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
        retention_days: int = 30,
    ) -> None:
        self._repo, self._endpoints, self._delivery = event_log_repo, endpoint_repo, delivery
        self._retention_days = retention_days
        self._task: asyncio.Task | None = None
        self._wake = asyncio.Event()
        self._stopping = False
        self.error: str | None = None
        event_publisher.subscribe(self._handle_domain_event)

    async def _handle_domain_event(self, event: DomainEvent) -> None:
        payload = asdict(event)
        payload["timestamp"] = event.timestamp.isoformat()
        replication = ReplicationEvent(
            str(uuid.uuid4()), event.event_type, event.timestamp, payload
        )
        endpoints = await self._endpoints.list_all()
        targets = [
            ep.id
            for ep in endpoints
            if ep.enabled and (not ep.event_types or event.event_type in ep.event_types)
        ]
        # Event, target deliveries and alarm projection commit together.
        await self._repo.record(replication, targets)
        self._wake.set()

    async def start(self) -> None:
        if self._task is None:
            self._stopping = False
            self._task = asyncio.create_task(self._run(), name="webhook-outbox")

    async def stop(self) -> None:
        if self._task is None:
            return
        self._stopping = True
        self._wake.set()
        try:
            async with asyncio.timeout(15):
                await asyncio.shield(self._task)
        except TimeoutError:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
        self._task = None

    async def _send(self, delivery: dict) -> None:
        success = await self._delivery.deliver(delivery["event"], delivery["endpoint"])
        await self._repo.finish_delivery(delivery["id"], success, time.time())

    async def _run(self) -> None:
        next_prune = 0.0
        while not self._stopping:
            self._wake.clear()
            try:
                pending = await self._repo.pending_deliveries(time.time())
                if pending:
                    # At most four endpoints; each endpoint retains event order.
                    results = await asyncio.gather(
                        *(self._send(item) for item in pending), return_exceptions=True
                    )
                    failures = [r for r in results if isinstance(r, BaseException)]
                    if failures:
                        raise RuntimeError("Outbox batch failed") from failures[0]
                if time.monotonic() >= next_prune:
                    cutoff = datetime.now(UTC) - timedelta(days=self._retention_days)
                    await self._repo.prune(cutoff.isoformat())
                    next_prune = time.monotonic() + 60
                self.error = None
                if pending:
                    continue
            except Exception as exc:
                self.error = str(exc)
                logger.exception("Outbox worker failed; durable deliveries will be retried")
            try:
                await asyncio.wait_for(self._wake.wait(), timeout=0.5)
            except TimeoutError:
                pass

    async def list_recent_events(self, limit: int = 50) -> list[ReplicationEvent]:
        return await self._repo.list_recent(limit)

    async def delivery_history(self, limit: int = 100) -> list[dict]:
        return await self._repo.delivery_history(limit)

    async def check(self) -> None:
        await self._repo.check()
