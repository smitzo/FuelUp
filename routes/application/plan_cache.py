import hashlib
import json
import time
import uuid

from django.conf import settings
from django.core.cache import cache

CACHE_SCHEMA_VERSION = "route-plan:v2"
LOCK_SECONDS = 30
LOCK_WAIT_SECONDS = 2
LOCK_POLL_SECONDS = 0.05


def get_or_build_route_plan(start, finish, builder):
    cache_key = _route_cache_key(start, finish)
    cached = cache.get(cache_key)
    if cached is not None:
        return cached, "HIT"

    lock_key = f"{cache_key}:lock"
    lock_token = uuid.uuid4().hex
    has_lock = cache.add(lock_key, lock_token, LOCK_SECONDS)
    if has_lock:
        try:
            result = builder(start, finish)
            cache.set(cache_key, result, settings.ROUTE_CACHE_SECONDS)
            return result, "MISS"
        finally:
            if cache.get(lock_key) == lock_token:
                cache.delete(lock_key)

    deadline = time.monotonic() + LOCK_WAIT_SECONDS
    while time.monotonic() < deadline:
        time.sleep(LOCK_POLL_SECONDS)
        cached = cache.get(cache_key)
        if cached is not None:
            return cached, "HIT"

    result = builder(start, finish)
    cache.set(cache_key, result, settings.ROUTE_CACHE_SECONDS)
    return result, "MISS"


def _route_cache_key(start, finish):
    payload = json.dumps(
        {
            "version": CACHE_SCHEMA_VERSION,
            "start": _normalize_location(start),
            "finish": _normalize_location(finish),
            "range_miles": 500,
            "mpg": 10,
            "alternatives": settings.ROUTE_ALTERNATIVES,
            "geometry_overview": settings.ROUTE_GEOMETRY_OVERVIEW,
            "time_value": settings.ROUTE_TIME_VALUE_USD_PER_HOUR,
            "stop_penalty": settings.ROUTE_STOP_PENALTY_USD,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    digest = hashlib.sha256(payload.encode()).hexdigest()
    return f"fuelup:{CACHE_SCHEMA_VERSION}:{digest}"


def _normalize_location(value):
    return " ".join(value.strip().casefold().split())
