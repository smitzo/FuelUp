import hashlib
import logging
import time

from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse

logger = logging.getLogger(__name__)


class RouteRateLimitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method != "POST" or request.path.rstrip("/") != "/api/route":
            return self.get_response(request)

        quota = _consume_quota(_client_identifier(request))
        if quota is None:
            return self.get_response(request)

        limit, remaining, reset_seconds = quota
        if remaining < 0:
            response = JsonResponse(
                {
                    "error": {
                        "code": "rate_limit_exceeded",
                        "message": (
                            "Too many route requests. Retry after the "
                            "rate-limit window resets."
                        ),
                    }
                },
                status=429,
            )
            response["Retry-After"] = str(reset_seconds)
        else:
            response = self.get_response(request)

        response["X-RateLimit-Limit"] = str(limit)
        response["X-RateLimit-Remaining"] = str(max(0, remaining))
        response["X-RateLimit-Reset"] = str(reset_seconds)
        return response


def _consume_quota(identifier):
    limit = settings.ROUTE_RATE_LIMIT_REQUESTS
    window_seconds = settings.ROUTE_RATE_LIMIT_WINDOW_SECONDS
    if limit <= 0 or window_seconds <= 0:
        return None

    now = int(time.time())
    window = now // window_seconds
    reset_seconds = window_seconds - (now % window_seconds)
    digest = hashlib.sha256(identifier.encode()).hexdigest()
    key = f"fuelup:rate-limit:v1:{window}:{digest}"

    try:
        if cache.add(key, 1, timeout=window_seconds + 1):
            count = 1
        else:
            count = cache.incr(key)
    except Exception:
        logger.exception("rate_limit_cache_error")
        return None
    if not isinstance(count, int):
        logger.warning("rate_limit_cache_unavailable")
        return None
    return limit, limit - count, reset_seconds


def _client_identifier(request):
    if settings.TRUST_PROXY_HEADERS:
        forwarded_for = request.headers.get("X-Forwarded-For", "")
        if forwarded_for:
            return forwarded_for.split(",", 1)[0].strip()
    return request.META.get("REMOTE_ADDR") or "unknown"
