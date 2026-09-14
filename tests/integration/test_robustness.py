import asyncio
import time
from unittest.mock import AsyncMock

import pytest

from bacnet_lab.adapters.bacnet.device_factory import load_all_devices
from bacnet_lab.adapters.http.app import create_app
from bacnet_lab.adapters.persistence.sqlite_repos import SqliteDeviceRepository
from bacnet_lab.adapters.scenarios.alarm import AlarmScenario
from bacnet_lab.adapters.scenarios.device_offline import DeviceOfflineScenario
from bacnet_lab.adapters.scenarios.hvac_day_cycle import HvacDayCycleScenario
from bacnet_lab.adapters.scenarios.manual_override import ManualOverrideScenario
from bacnet_lab.domain.enums import DeviceStatus, EventType, ScenarioStatus
from tests.integration.test_api import make_test_client


@pytest.fixture
async def lab():
    async with make_test_client() as client:
        c = client._transport.app.state.container
        for cls in (
            AlarmScenario,
            ManualOverrideScenario,
            HvacDayCycleScenario,
            DeviceOfflineScenario,
        ):
            c.scenario_service._runner.register(cls(c.device_service, c.event_publisher))
        try:
            yield client, c
        finally:
            await c.scenario_service.stop_all()
            await c.event_service.stop()


async def until(predicate):
    async with asyncio.timeout(2):
        while not predicate():
            await asyncio.sleep(0.005)


@pytest.mark.asyncio
async def test_alarm_projection_lifecycle_and_cancellation(lab):
    client, c = lab
    await client.post("/api/scenarios/alarm_cycle/start", json={"params": {"alarm_duration": 30}})
    async with asyncio.timeout(2):
        while not await c.alarm_repo.get_active():
            await asyncio.sleep(0.005)
    assert c.device_service.point(1001, "AHU-01/SupplyAirTemp").present_value == 35
    assert (await client.post("/api/scenarios/alarm_cycle/stop")).status_code == 200
    assert not await c.alarm_repo.get_active()
    assert c.device_service.point(1001, "AHU-01/SupplyAirTemp").present_value == 22.5
    kinds = [e.event_type for e in await c.event_service.list_recent_events()]
    assert EventType.ALARM_RAISED in kinds and EventType.ALARM_CLEARED in kinds
    assert EventType.SCENARIO_STARTED in kinds and EventType.SCENARIO_STOPPED in kinds


@pytest.mark.asyncio
async def test_override_preserves_prior_command_and_excludes_simulation(lab):
    client, c = lab
    await c.device_service.write_point_by_name(1001, "AHU-01/CoolingValve", 77)
    assert (await client.post("/api/scenarios/manual_override/start")).status_code == 200
    await until(lambda: c.device_service.point(1001, "AHU-01/CoolingValve").present_value == 100)
    await c.device_service.write_point_by_name(
        1001, "AHU-01/CoolingValve", 0, owner="hvac_day_cycle"
    )
    assert c.device_service.point(1001, "AHU-01/CoolingValve").present_value == 100
    response = await client.put(
        "/api/devices/1001/points", json={"point_name": "AHU-01/CoolingValve", "value": 50}
    )
    assert response.status_code == 409
    await client.post("/api/scenarios/manual_override/stop")
    assert c.device_service.point(1001, "AHU-01/CoolingValve").present_value == 77


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "params",
    [
        {"cycle_seconds": 0},
        {"interval": -1},
        {"interval": "abc"},
        {"interval": 10**400},
        {"typo": 10},
    ],
)
async def test_invalid_scenario_parameters_rejected_before_start(lab, params):
    client, c = lab
    response = await client.post("/api/scenarios/hvac_day_cycle/start", json={"params": params})
    assert response.status_code == 422
    assert c.scenario_service.get_scenario("hvac_day_cycle").status == ScenarioStatus.IDLE


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "name,value",
    [
        ("AHU-01/CoolingValve", "hello"),
        ("AHU-01/CoolingValve", True),
        ("AHU-01/CoolingValve", 101),
        ("AHU-01/SupplyFanEnable", 1),
        ("AHU-01/SupplyFanEnable", "false"),
    ],
)
async def test_point_type_validation(lab, name, value):
    client, _ = lab
    assert (
        await client.put("/api/devices/1001/points", json={"point_name": name, "value": value})
    ).status_code == 422


@pytest.mark.asyncio
async def test_write_by_identifier_and_effective_value(lab):
    client, c = lab
    url = "/api/devices/1001/points"
    await client.put(
        url, json={"object_type": "analogOutput", "object_instance": 1, "value": 88, "priority": 8}
    )
    response = await client.put(url, json={"point_name": "AHU-01/CoolingValve", "value": 55})
    assert response.status_code == 200 and response.json()["present_value"] == 88
    response = await client.put(
        url, json={"point_name": "AHU-01/CoolingValve", "value": None, "priority": 8}
    )
    assert response.json()["present_value"] == 55
    # An external BACnet mutation must be reconciled before serving API reads.
    await c.device_service._network.write_point_value(
        1001, c.device_service.point(1001, "AHU-01/CoolingValve").object_type, 1, 62
    )
    values = (await client.get("/api/devices/1001")).json()["points"]
    assert (
        next(p["present_value"] for p in values if p["object_name"] == "AHU-01/CoolingValve") == 62
    )


@pytest.mark.asyncio
async def test_unchanged_value_does_not_emit_event(lab):
    _, c = lab
    before = len(await c.event_service.list_recent_events())
    await c.device_service.write_point_by_name(1001, "AHU-01/CoolingValve", 45)
    assert len(await c.event_service.list_recent_events()) == before


@pytest.mark.asyncio
async def test_slow_webhook_is_off_the_write_path(lab, monkeypatch):
    _, c = lab
    await c.endpoint_service.create_endpoint("https://example.com")
    entered = asyncio.Event()
    release = asyncio.Event()

    async def deliver(*args):
        entered.set()
        await release.wait()
        return True

    monkeypatch.setattr(c.event_service._delivery, "deliver", deliver)
    await c.event_service.start()
    try:
        await asyncio.wait_for(
            c.device_service.write_point_by_name(1001, "AHU-01/CoolingValve", 50), 0.5
        )
        await asyncio.wait_for(entered.wait(), 1)
        await asyncio.wait_for(
            c.device_service.write_point_by_name(1001, "AHU-01/CoolingValve", 60), 0.5
        )
    finally:
        release.set()


@pytest.mark.asyncio
async def test_outbox_retry_survives_worker_restart_and_preserves_endpoint_order(lab):
    _, c = lab
    await c.endpoint_service.create_endpoint("https://example.com")
    await c.device_service.write_point_by_name(1001, "AHU-01/CoolingValve", 50)
    await c.device_service.write_point_by_name(1001, "AHU-01/CoolingValve", 60)
    repo = c.event_service._repo
    pending = await repo.pending_deliveries(time.time())
    assert len(pending) == 1
    first = pending[0]["id"]
    await repo.finish_delivery(first, False, time.time())
    assert not await repo.pending_deliveries(time.time())
    reopened = type(repo)(c.settings.db_path)
    assert (await reopened.pending_deliveries(time.time() + 100))[0]["id"] == first
    await reopened.finish_delivery(first, True, time.time())
    second = await reopened.pending_deliveries(time.time())
    assert len(second) == 1 and second[0]["id"] != first
    assert (await reopened.delivery_history())[1]["attempts"] == 2


@pytest.mark.asyncio
async def test_delivery_gives_up_after_five_attempts(lab):
    _, c = lab
    await c.endpoint_service.create_endpoint("https://example.com")
    await c.device_service.write_point_by_name(1001, "AHU-01/CoolingValve", 50)
    repo = c.event_service._repo
    delivery = (await repo.pending_deliveries(time.time()))[0]
    for _ in range(5):
        await repo.finish_delivery(delivery["id"], False, time.time())
    assert (await repo.delivery_history())[0]["state"] == "failed"
    assert not await repo.pending_deliveries(time.time() + 10000)


@pytest.mark.asyncio
async def test_endpoints_hide_secrets_and_reject_untrusted_hosts(lab):
    client, _ = lab
    created = await client.post("/api/endpoints", json={"url": "https://example.com/hook"})
    assert created.status_code == 201 and created.json()["secret"]
    assert "secret" not in (await client.get("/api/endpoints")).json()[0]
    for url in [
        "file:///etc/passwd",
        "not-a-url",
        "http://169.254.169.254/",
        "https://example.com@evil.test/hook",
    ]:
        assert (await client.post("/api/endpoints", json={"url": url})).status_code == 422


@pytest.mark.asyncio
async def test_auth_does_not_mask_application_error(lab, monkeypatch):
    from httpx import ASGITransport, AsyncClient

    _, c = lab
    monkeypatch.setattr(
        c.device_service, "list_devices", AsyncMock(side_effect=RuntimeError("database failure"))
    )
    app = create_app(container=c, auth_username="admin", auth_password="secret")
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test"
    ) as ac:
        assert (await ac.get("/api/devices", auth=("admin", "secret"))).status_code == 500


@pytest.mark.asyncio
async def test_health_reports_actual_errors_and_limits_are_bounded(lab):
    client, c = lab
    c.device_service._devices[1001].status = DeviceStatus.ERROR
    response = await client.get("/api/health")
    assert response.status_code == 503 and response.json()["online_devices"] == 6
    for path in ["/api/events?limit=-1", "/api/alarms?limit=1000000", "/api/deliveries?limit=0"]:
        assert (await client.get(path)).status_code == 422
    assert (
        await client.post(
            "/api/scenarios/alarm_cycle/start", headers={"Origin": "https://evil.test"}
        )
    ).status_code == 403


@pytest.mark.asyncio
async def test_sqlite_reconcile_and_numeric_roundtrip(lab):
    _, c = lab
    repo = SqliteDeviceRepository(c.settings.db_path)
    device = load_all_devices("config/devices")[0]
    device.points[0].present_value = 1e-7
    device.points = device.points[:1]
    await repo.save(device)
    await repo.reconcile({device.device_id})
    assert len(await repo.list_all()) == 1
    loaded = await repo.get(device.device_id)
    assert len(loaded.points) == 1 and loaded.points[0].present_value == pytest.approx(1e-7)


@pytest.mark.asyncio
async def test_ui_refresh_keeps_controls_and_all_pages_render(lab):
    client, _ = lab
    page = (await client.get("/ui/devices/1001")).text
    partial = (await client.get("/ui/partials/points/1001")).text
    assert page.count('data-method="PUT"') == partial.count('data-method="PUT"') == 7
    assert 'data-kind="boolean"' in partial
    for path in ["/ui/scenarios", "/ui/events", "/ui/endpoints", "/ui/partials/endpoints"]:
        assert (await client.get(path)).status_code == 200
    assert "https://unpkg.com" not in page


@pytest.mark.asyncio
async def test_lifespan_cleanup_runs_after_failure(lab, monkeypatch):
    _, c = lab
    cleanup = AsyncMock()
    monkeypatch.setattr(c, "close", cleanup)
    monkeypatch.setattr(c, "start", AsyncMock(side_effect=RuntimeError("startup failed")))
    app = create_app(container=c)
    with pytest.raises(RuntimeError, match="startup failed"):
        async with app.router.lifespan_context(app):
            pass
    cleanup.assert_awaited_once()


@pytest.mark.asyncio
async def test_completion_recording_failure_is_visible_without_unhandled_task(lab):
    _, c = lab
    scenario = c.scenario_service._runner._scenarios["manual_override"]
    scenario.run = AsyncMock()
    publisher = scenario._event_publisher
    original = publisher.publish
    try:
        publisher.publish = AsyncMock(side_effect=OSError("storage unavailable"))
        await scenario._run_wrapper()
        assert scenario.to_domain().status == ScenarioStatus.ERROR
        assert "storage unavailable" in scenario.to_domain().error
    finally:
        publisher.publish = original


@pytest.mark.asyncio
async def test_stop_all_cleans_remaining_scenarios_after_failure(lab):
    _, c = lab
    registry = c.scenario_service._runner
    scenarios = list(registry._scenarios.values())
    originals = [scenario.stop for scenario in scenarios]
    try:
        for scenario in scenarios:
            scenario.stop = AsyncMock()
        scenarios[0].stop.side_effect = RuntimeError("cleanup failed")
        with pytest.raises(ExceptionGroup):
            await registry.stop_all()
        assert all(scenario.stop.await_count == 1 for scenario in scenarios)
    finally:
        for scenario, original in zip(scenarios, originals):
            scenario.stop = original


@pytest.mark.asyncio
async def test_override_retains_later_external_command_even_at_identical_value(lab):
    client, c = lab
    await client.post("/api/scenarios/manual_override/start")
    await until(lambda: c.device_service.point(1001, "AHU-01/CoolingValve").present_value == 100)
    point = c.device_service.point(1001, "AHU-01/CoolingValve")
    await c.device_service._network.write_point_value(
        1001, point.object_type, point.object_instance, 100, 8
    )
    await client.post("/api/scenarios/manual_override/stop")
    assert c.device_service.point(1001, "AHU-01/CoolingValve").present_value == 100
