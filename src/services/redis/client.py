"""Redis client implementation."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

import redis

from src.config import (
    get_redis_connect_timeout_seconds,
    get_redis_host,
    get_redis_password,
    get_redis_port,
    get_redis_socket_timeout_seconds,
    get_redis_ssl_enabled,
    get_redis_url,
    get_redis_username,
)

_redis_client: redis.Redis | None = None


def describe_redis_target() -> str:
    redis_url = get_redis_url()
    if redis_url:
        parsed = urlparse(redis_url)
        host = parsed.hostname or "unknown"
        port = parsed.port or (6380 if parsed.scheme == "rediss" else 6379)
        return f"{host}:{port} (from REDIS_URL)"

    return f"{get_redis_host()}:{get_redis_port()}"


def get_redis_client() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = _create_redis_client()
    return _redis_client


def ping_redis() -> bool:
    return bool(get_redis_client().ping())


def _create_redis_client() -> redis.Redis:
    redis_url = get_redis_url()
    if redis_url:
        return redis.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=get_redis_connect_timeout_seconds(),
            socket_timeout=get_redis_socket_timeout_seconds(),
        )

    connect_kwargs: dict[str, Any] = {
        "host": get_redis_host(),
        "port": get_redis_port(),
        "password": get_redis_password(),
        "username": get_redis_username(),
        "decode_responses": True,
        "socket_connect_timeout": get_redis_connect_timeout_seconds(),
        "socket_timeout": get_redis_socket_timeout_seconds(),
    }
    if get_redis_ssl_enabled():
        connect_kwargs["ssl"] = True
        connect_kwargs["ssl_cert_reqs"] = None

    return redis.Redis(**connect_kwargs)
