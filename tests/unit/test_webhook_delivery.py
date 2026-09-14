import hashlib
import hmac
from datetime import UTC, datetime

import httpx
import pytest

from bacnet_lab.adapters.webhook.delivery import WebhookDeliveryAdapter
from bacnet_lab.domain.enums import EventType
from bacnet_lab.domain.models.endpoint import OutboundEndpoint
from bacnet_lab.domain.models.event import ReplicationEvent


@pytest.mark.asyncio
async def test_signature_matches_exact_wire_bytes_and_redirects_fail():
    captured = []

    def handle(request):
        captured.append(request)
        return httpx.Response(302, headers={"Location": "http://elsewhere.invalid"})

    adapter = WebhookDeliveryAdapter()
    await adapter.close()
    adapter._client = httpx.AsyncClient(
        transport=httpx.MockTransport(handle), follow_redirects=False
    )
    try:
        endpoint = OutboundEndpoint("ep", "http://localhost/hook", "secret")
        event = ReplicationEvent(
            "event", EventType.TELEMETRY_SNAPSHOT, datetime.now(UTC), {"name": "Température"}
        )
        assert not await adapter.deliver(event, endpoint)
        request = captured[0]
        expected = hmac.new(b"secret", request.content, hashlib.sha256).hexdigest()
        assert request.headers["X-BACnetLab-Signature"] == "sha256=" + expected
        assert len(captured) == 1
    finally:
        await adapter.close()


@pytest.mark.asyncio
async def test_persisted_endpoint_is_revalidated_before_sending():
    calls = []
    adapter = WebhookDeliveryAdapter(allowed_hosts=["localhost"])
    await adapter.close()
    adapter._client = httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: calls.append(request) or httpx.Response(200))
    )
    try:
        event = ReplicationEvent("event", EventType.TELEMETRY_SNAPSHOT, datetime.now(UTC), {})
        endpoint = OutboundEndpoint("legacy", "http://old-destination.invalid/hook", "secret")
        assert not await adapter.deliver(event, endpoint)
        assert calls == []
    finally:
        await adapter.close()
