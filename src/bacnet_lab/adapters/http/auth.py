from __future__ import annotations

import secrets

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class BasicAuthMiddleware(BaseHTTPMiddleware):
    """HTTP Basic Auth middleware — equivalent to htaccess/htpasswd.

    The browser shows a native login popup. Credentials are cached
    by the browser for the session (no re-prompt on every page).
    """

    def __init__(self, app, username: str, password: str) -> None:
        super().__init__(app)
        self._username = username
        self._password = password

    async def dispatch(self, request: Request, call_next) -> Response:
        auth = request.headers.get("Authorization")
        if auth and auth.startswith("Basic "):
            import base64

            try:
                decoded = base64.b64decode(auth[6:]).decode("utf-8")
                provided_user, provided_pass = decoded.split(":", 1)
                user_ok = secrets.compare_digest(provided_user, self._username)
                pass_ok = secrets.compare_digest(provided_pass, self._password)
                if user_ok and pass_ok:
                    return await call_next(request)
            except Exception:
                pass

        return Response(
            status_code=401,
            headers={"WWW-Authenticate": 'Basic realm="BACnet Lab"'},
            content="Unauthorized",
        )
