import pytest
from pydantic import ValidationError

from bacnet_lab.adapters.bacnet.device_factory import load_all_devices
from bacnet_lab.infrastructure.config import AuthSettings, load_settings


def test_partial_auth_fails_closed():
    with pytest.raises(ValidationError):
        AuthSettings(username="admin")


def test_dotenv_then_environment_precedence(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("BACNET_LAB_HTTP_PORT=8123\n")
    assert load_settings().http.port == 8123
    monkeypatch.setenv("BACNET_LAB_HTTP_PORT", "8124")
    assert load_settings().http.port == 8124


def test_invalid_config_is_rejected(tmp_path):
    config = tmp_path / "settings.yaml"
    config.write_text("http:\n  port: 70000\n")
    with pytest.raises(ValidationError):
        load_settings(str(config))


def test_duplicate_devices_rejected(tmp_path):
    template = "device_id: 1001\nname: Example\npoints: []\n"
    (tmp_path / "a.yaml").write_text(template)
    (tmp_path / "b.yaml").write_text(template)
    with pytest.raises(ValueError, match="unique"):
        load_all_devices(str(tmp_path))


def test_infinite_worker_interval_is_rejected():
    from bacnet_lab.infrastructure.config import AppSettings

    with pytest.raises(ValidationError):
        AppSettings(snapshot_interval=float("inf"))
