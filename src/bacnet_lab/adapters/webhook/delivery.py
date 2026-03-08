from __future__ import annotations

import hashlib
import hmac
import json
import logging

import httpx

from bacnet_lab.domain.models.endpoint import OutboundEndpoint
from bacnet_lab.domain.models.event import ReplicationEvent
from bacnet_lab.ports.event_delivery import EventDeliveryPort

logger = logging.getLogger(__name__)


class WebhookDeliveryAdapter(EventDeliveryPort):
    def __init__(self, timeout: float = 10.0) -> None:
        self._timeout = timeout

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
        signature = hmac.new(
            endpoint.secret.encode(), payload.encode(), hashlib.sha256
        ).hexdigest()

        headers = {
            "Content-Type": "application/json",
            "X-BACnetLab-Signature": f"sha256={signature}",
            "X-BACnetLab-Event": event.event_type.value,
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(endpoint.url, content=payload, headers=headers)
                success = 200 <= response.status_code < 300
                if not success:
                    logger.warning(
                        "Webhook delivery to %s returned %d", endpoint.url, response.status_code
                    )
                return success
        except Exception as e:
            logger.error("Webhook delivery to %s failed: %s", endpoint.url, e)
            return False
