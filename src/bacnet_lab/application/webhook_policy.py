from urllib.parse import urlsplit

from bacnet_lab.domain.errors import ValidationError


def validate_webhook_url(url: str, allowed_hosts: set[str]) -> None:
    try:
        parsed = urlsplit(url)
        _ = parsed.port
    except ValueError as exc:
        raise ValidationError("Invalid webhook URL") from exc
    if (
        parsed.scheme not in ("http", "https")
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.fragment
    ):
        raise ValidationError("Use an HTTP(S) URL without credentials or fragment")
    if parsed.hostname.lower() not in allowed_hosts:
        raise ValidationError("Webhook host is not in BACNET_LAB_WEBHOOK_ALLOWED_HOSTS")
