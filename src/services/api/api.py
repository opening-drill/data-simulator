import json
from urllib import error, request

from src.config import get_dispatch_timeout_seconds, get_dispatch_url
from src.config.constants import CONTENT_TYPE_JSON
from src.services.api.auth import get_bearer_token, invalidate_bearer_token


def dispatch_simulation_payloads(
    payloads: dict[str, object] | list[dict[str, object]],
    dispatch_url: str | None = None,
    timeout_seconds: float | None = None,
) -> dict[str, object] | list[dict[str, object]]:
    resolved_dispatch_url = dispatch_url or get_dispatch_url()
    resolved_timeout_seconds = timeout_seconds or get_dispatch_timeout_seconds()
    payload_list = payloads if isinstance(payloads, list) else [payloads]

    responses = [
        post_json(
            url=resolved_dispatch_url,
            payload=payload,
            timeout_seconds=resolved_timeout_seconds,
        )
        for payload in payload_list
    ]

    if isinstance(payloads, list):
        return responses

    return responses[0]


def post_json(
    url: str,
    payload: dict[str, object],
    timeout_seconds: float,
    *,
    _retried_after_auth: bool = False,
) -> dict[str, object]:
    request_body = json.dumps(payload).encode("utf-8")
    http_request = request.Request(
        url=url,
        data=request_body,
        headers={
            "Content-Type": CONTENT_TYPE_JSON,
            "Authorization": f"Bearer {get_bearer_token()}",
        },
        method="POST",
    )

    try:
        with request.urlopen(http_request, timeout=timeout_seconds) as response:
            response_body = response.read().decode("utf-8")
    except error.HTTPError as exc:
        if exc.code == 401 and not _retried_after_auth:
            invalidate_bearer_token()
            return post_json(
                url,
                payload,
                timeout_seconds,
                _retried_after_auth=True,
            )
        error_body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"API request failed with status {exc.code} at {url}: {error_body}"
        ) from exc
    except error.URLError as exc:
        raise RuntimeError(f"Could not reach API endpoint {url}: {exc.reason}") from exc

    if not response_body:
        return {"success": True}

    try:
        return json.loads(response_body)
    except json.JSONDecodeError:
        return {"success": True, "raw_response": response_body}
