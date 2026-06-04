"""JWT auth for Live-Data dispatch (login + cached Bearer token)."""

from __future__ import annotations

import json
import threading
from urllib import error, request
from src.config.settings import (
    get_auth_login_url,
    get_auth_password,
    get_auth_token_override,
    get_auth_username,
    get_dispatch_timeout_seconds,
)

_lock = threading.Lock()
_cached_token: str | None = None


def get_bearer_token(*, force_refresh: bool = False) -> str:
    override = get_auth_token_override()
    if override:
        return override

    global _cached_token
    with _lock:
        if force_refresh or not _cached_token:
            _cached_token = _login()
        return _cached_token


def invalidate_bearer_token() -> None:
    global _cached_token
    with _lock:
        _cached_token = None


def _login() -> str:
    login_url = get_auth_login_url()
    request_body = json.dumps(
        {"username": get_auth_username(), "password": get_auth_password()}
    ).encode("utf-8")
    http_request = request.Request(
        login_url,
        data=request_body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with request.urlopen(
            http_request,
            timeout=get_dispatch_timeout_seconds(),
        ) as response:
            response_body = response.read().decode("utf-8")
    except error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Live-Data login failed with status {exc.code} at {login_url}: {error_body}"
        ) from exc
    except error.URLError as exc:
        raise RuntimeError(
            f"Could not reach Live-Data login at {login_url}: {exc.reason}"
        ) from exc

    try:
        payload = json.loads(response_body)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Live-Data login returned non-JSON from {login_url}: {response_body[:200]}"
        ) from exc

    token = payload.get("token")
    if not token or not isinstance(token, str):
        raise RuntimeError(
            f"Live-Data login response missing token at {login_url}: {payload}"
        )

    return token
