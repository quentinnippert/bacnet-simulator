from __future__ import annotations

import logging
from dataclasses import dataclass

from bacnet_lab.adapters.bacnet.device_factory import load_all_devices
from bacnet_lab.adapters.bacnet.engine import BAC0Engine
from bacnet_lab.adapters.event_bus.in_process import InProcessEventPublisher
from bacnet_lab.adapters.persistence.migrations import run_migrations
from bacnet_lab.adapters.persistence.sqlite_repos import (
    SqliteAlarmRepository,
    SqliteDeviceRepository,
    SqliteEndpointRepository,
    SqliteEventLogRepository,
)
from bacnet_lab.adapters.scenarios.alarm import AlarmScenario
from bacnet_lab.adapters.scenarios.device_offline import DeviceOfflineScenario
from bacnet_lab.adapters.scenarios.hvac_day_cycle import HvacDayCycleScenario
from bacnet_lab.adapters.scenarios.manual_override import ManualOverrideScenario
from bacnet_lab.adapters.scenarios.registry import ScenarioRegistry
from bacnet_lab.adapters.webhook.delivery import WebhookDeliveryAdapter
from bacnet_lab.application.device_service import DeviceService
from bacnet_lab.application.endpoint_service import EndpointService
from bacnet_lab.application.event_service import EventService
from bacnet_lab.application.scenario_service import ScenarioService
from bacnet_lab.application.telemetry_service import TelemetryService
from bacnet_lab.infrastructure.config import AppSettings

logger = logging.getLogger(__name__)


@dataclass
class Container:
    settings: AppSettings
    device_service: DeviceService
    scenario_service: ScenarioService
    endpoint_service: EndpointService
    event_service: EventService
    telemetry_service: TelemetryService
    alarm_repo: SqliteAlarmRepository
    engine: BAC0Engine
    event_publisher: InProcessEventPublisher


async def create_container(settings: AppSettings) -> Container:
    # Run DB migrations
    await run_migrations(settings.db_path)

    # Adapters
    engine = BAC0Engine(ip=settings.bacnet.ip)
    event_publisher = InProcessEventPublisher()
    webhook_delivery = WebhookDeliveryAdapter()

    # Repositories
    device_repo = SqliteDeviceRepository(settings.db_path)
    endpoint_repo = SqliteEndpointRepository(settings.db_path)
    event_log_repo = SqliteEventLogRepository(settings.db_path)
    alarm_repo = SqliteAlarmRepository(settings.db_path)

    # Application services
    device_service = DeviceService(
        device_repo=device_repo,
        network=engine,
        event_publisher=event_publisher,
        bacnet_port_start=settings.bacnet.port_start,
    )

    # Scenarios
    scenario_registry = ScenarioRegistry()
    scenario_registry.register(HvacDayCycleScenario(device_service, event_publisher))
    scenario_registry.register(AlarmScenario(device_service, event_publisher))
    scenario_registry.register(DeviceOfflineScenario(device_service, event_publisher))
    scenario_registry.register(ManualOverrideScenario(device_service, event_publisher))

    scenario_service = ScenarioService(runner=scenario_registry)

    endpoint_service = EndpointService(
        repo=endpoint_repo,
        delivery=webhook_delivery,
    )

    event_service = EventService(
        event_publisher=event_publisher,
        event_log_repo=event_log_repo,
        endpoint_repo=endpoint_repo,
        delivery=webhook_delivery,
    )

    telemetry_service = TelemetryService(event_publisher=event_publisher)
    telemetry_service.set_device_service(device_service)

    # Load and initialize devices
    devices = load_all_devices(settings.devices_dir)
    await device_service.initialize_devices(devices)

    logger.info("Container initialized: %d devices loaded", len(devices))

    return Container(
        settings=settings,
        device_service=device_service,
        scenario_service=scenario_service,
        endpoint_service=endpoint_service,
        event_service=event_service,
        telemetry_service=telemetry_service,
        alarm_repo=alarm_repo,
        engine=engine,
        event_publisher=event_publisher,
    )
