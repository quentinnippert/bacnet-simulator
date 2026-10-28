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


def test_auto_bacnet_ip_uses_default_route_address(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("BACNET_LAB_BACNET_IP", "auto")
    monkeypatch.setenv("BACNET_LAB_BACNET_PREFIX", "24")

    class RouteSocket:
        destination = None

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def connect(self, destination):
            self.destination = destination

        def getsockname(self):
            return ("192.168.1.25", 0)

    route_socket = RouteSocket()
    monkeypatch.setattr(
        "bacnet_lab.infrastructure.config.socket.socket", lambda *_args: route_socket
    )

    settings = load_settings()

    assert settings.bacnet.ip == "192.168.1.25"
    assert settings.bacnet.prefix == 24
    assert route_socket.destination == ("192.0.2.1", 9)


def test_auto_http_host_uses_default_route_address(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("BACNET_LAB_HTTP_HOST", "auto")

    class RouteSocket:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def connect(self, destination):
            self.destination = destination

        def getsockname(self):
            return ("10.20.30.40", 0)

    route_socket = RouteSocket()
    monkeypatch.setattr(
        "bacnet_lab.infrastructure.config.socket.socket", lambda *_args: route_socket
    )

    settings = load_settings()

    assert settings.http.host == "10.20.30.40"
    assert route_socket.destination == ("192.0.2.1", 9)


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
