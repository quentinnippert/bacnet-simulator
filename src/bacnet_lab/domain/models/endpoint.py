from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from bacnet_lab.domain.enums import EventType


@dataclass
class OutboundEndpoint:
    id: str
    url: str
    secret: str
    enabled: bool = True
    event_types: list[EventType] = field(default_factory=list)
    created_at: datetime | None = None
    last_delivery_at: datetime | None = None
    failure_count: int = 0
