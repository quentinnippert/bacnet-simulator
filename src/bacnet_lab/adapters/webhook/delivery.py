from __future__ import annotations

import hashlib
import hmac
import json
import logging

import httpx

from bacnet_lab.application.webhook_policy import validate_webhook_url
from bacnet_lab.domain.models.endpoint import OutboundEndpoint
from bacnet_lab.domain.models.event import ReplicationEvent
from bacnet_lab.ports.event_delivery import EventDeliveryPort

logger = logging.getLogger(__name__)


class WebhookDeliveryAdapter(EventDeliveryPort):
    def __init__(self, timeout: float = 10.0, allowed_hosts: list[str] | None = None) -> None:
        self._allowed_hosts = {
            host.lower()
            for host in (["localhost", "127.0.0.1"] if allowed_hosts is None else allowed_hosts)
        }
        self._client = httpx.AsyncClient(timeout=timeout, follow_redirects=False, trust_env=False)

    async def deliver(self, event: ReplicationEvent, endpoint: OutboundEndpoint) -> bool:
        payload = json.dumps(
            {
                "id": event.id,
                "event_type": event.event_type.value,
                "timestamp": event.timestamp.isoformat(),
                "payload": event.payload,
            },
            default=str,
        )
        signature = hmac.new(endpoint.secret.encode(), payload.encode(), hashlib.sha256).hexdigest()

        headers = {
            "Content-Type": "application/json",
            "X-BACnetLab-Signature": f"sha256={signature}",
            "X-BACnetLab-Event": event.event_type.value,
        }

        try:
            # Recheck persisted endpoints when configuration changes or data is migrated.
            validate_webhook_url(endpoint.url, self._allowed_hosts)
            response = await self._client.post(endpoint.url, content=payload, headers=headers)
            return 200 <= response.status_code < 300
        except (httpx.HTTPError, ValueError) as e:
            logger.error("Webhook delivery to %s failed: %s", endpoint.url, e)
            return False

    async def close(self) -> None:
        await self._client.aclose()
