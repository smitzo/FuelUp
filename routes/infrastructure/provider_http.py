"""Bounded backend-only JSON transport. Never log credentials or response bodies."""

import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from time import perf_counter

from django.conf import settings

from routes.application.provider_budget import reserve_request
from routes.application.provider_health import check_circuit, record_outcome
from routes.domain.exceptions import ExternalServiceError

logger = logging.getLogger("fuelup.providers")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # API credentials must never follow a redirect to another host.
        return None


def request_json(source_slug, base_url, path, *, headers=None, payload=None):
    parsed = urllib.parse.urlsplit(base_url)
    if parsed.scheme != "https" or parsed.username or parsed.password or parsed.query:
        raise ExternalServiceError("Provider URL must use HTTPS without credentials.")
    if not path.startswith("/") or path.startswith("//"):
        raise ExternalServiceError("Invalid provider request path.")
    check_circuit(source_slug)
    reserve_request(source_slug)
    request_headers = {
        "Accept": "application/json",
        "User-Agent": settings.EXTERNAL_API_USER_AGENT,
        **(headers or {}),
    }
    data = None
    if payload is not None:
        data = json.dumps(payload, allow_nan=False).encode()
        request_headers["Content-Type"] = "application/json"
    request = urllib.request.Request(
        base_url.rstrip("/") + path, data=data, headers=request_headers
    )
    started = perf_counter()
    error_code = ""
    try:
        with urllib.request.build_opener(NoRedirect).open(
            request, timeout=settings.EXTERNAL_API_TIMEOUT_SECONDS
        ) as response:
            raw = response.read(settings.PROVIDER_MAX_RESPONSE_BYTES + 1)
            if len(raw) > settings.PROVIDER_MAX_RESPONSE_BYTES:
                raise ValueError("oversized")
            result = json.loads(raw, parse_float=str)
    except urllib.error.HTTPError as exc:
        error_code = f"http_{exc.code}"
    except (urllib.error.URLError, TimeoutError, OSError):
        error_code = "network_error"
    except (ValueError, UnicodeError):
        error_code = "invalid_response"
    record_outcome(source_slug, error_code=error_code)
    logger.info(
        "provider_request",
        extra={
            "provider": source_slug,
            "outcome": error_code or "ok",
            "duration_ms": round((perf_counter() - started) * 1000),
        },
    )
    if error_code:
        raise ExternalServiceError(f"Provider request failed ({error_code}).")
    return result
