from unittest.mock import AsyncMock, Mock

import pytest
from httpx import ASGITransport, AsyncClient

from bacnet_lab import bootstrap
from bacnet_lab.adapters.http.app import create_app
from bacnet_lab.adapters.scenarios.registry import ScenarioRegistry
from bacnet_lab.bootstrap import Container
from bacnet_lab.infrastructure.config import AppSettings


@pytest.mark.parametrize("factories, expected", [(None, 6), ([], 0)])
async def test_container_scenario_defaults_and_explicit_empty(
    tmp_path, monkeypatch, factories, expected
):
    registry = ScenarioRegistry()
    registry.register = Mock(wraps=registry.register)
    monkeypatch.setattr(bootstrap, "ScenarioRegistry", lambda: registry)
    settings = AppSettings(db_path=str(tmp_path / "test.db"), devices_dir="missing-directory")
    resources = await bootstrap.create_container(settings, devices=[], scenario_factories=factories)
    try:
        assert registry.register.call_count == expected
        assert await resources.device_service.list_devices() == []
    finally:
        await resources.close()


async def test_app_factory_runs_in_lifespan_and_disables_demo_web():
    resources = Mock(spec=Container)
    resources.start = AsyncMock()
    resources.close = AsyncMock()
    factory = AsyncMock(return_value=resources)
    settings = AppSettings()
    app = create_app(settings=settings, container_factory=factory, include_web=False)
    factory.assert_not_awaited()
    async with app.router.lifespan_context(app):
        factory.assert_awaited_once_with(settings)
        resources.start.assert_awaited_once()
        assert app.state.container is resources
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            assert (await client.get("/ui/")).status_code == 404
    resources.close.assert_awaited_once()


async def test_factory_start_failure_still_closes_resources():
    resources = Mock(spec=Container)
    resources.start = AsyncMock(side_effect=RuntimeError("startup failed"))
    resources.close = AsyncMock()
    app = create_app(settings=AppSettings(), container_factory=AsyncMock(return_value=resources))
    with pytest.raises(RuntimeError, match="startup failed"):
        async with app.router.lifespan_context(app):
            pytest.fail("Failed startup must not serve requests")
    resources.close.assert_awaited_once()
