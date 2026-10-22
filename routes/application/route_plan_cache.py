import hashlib
import json
import time
import uuid
from dataclasses import asdict
from datetime import UTC, datetime

from django.conf import settings
from django.core.cache import cache

from routes.domain.price_resolver import RESOLVER_VERSION

CACHE_SCHEMA_VERSION = "market-route-plan:v3"
LOCK_SECONDS = 30
LOCK_POLL_SECONDS = 0.05


def get_or_build_route_plan(route_request, catalogue, market, builder):
    cache_key = _route_cache_key(route_request, catalogue, market)
    cached = cache.get(cache_key)
    if cached is not None:
        return cached, "HIT", _cache_ttl(catalogue, market)

    lock_key = f"{cache_key}:lock"
    lock_token = uuid.uuid4().hex
    has_lock = cache.add(lock_key, lock_token, LOCK_SECONDS)
    if has_lock:
        try:
            return _build_and_cache(cache_key, catalogue, market, builder)
        finally:
            if cache.get(lock_key) == lock_token:
                cache.delete(lock_key)
    if has_lock is None:
        return _build_and_cache(cache_key, catalogue, market, builder)

    deadline = time.monotonic() + settings.ROUTE_CACHE_LOCK_WAIT_SECONDS
    while time.monotonic() < deadline:
        time.sleep(LOCK_POLL_SECONDS)
        cached = cache.get(cache_key)
        if cached is not None:
            return cached, "HIT", _cache_ttl(catalogue, market)
    return _build_and_cache(cache_key, catalogue, market, builder)


def _build_and_cache(cache_key, catalogue, market, builder):
    result = builder()
    ttl = _cache_ttl(catalogue, market)
    cache.set(cache_key, result, ttl)
    return result, "MISS", ttl


def _route_cache_key(route_request, catalogue, market):
    request_payload = route_request.cache_payload()
    request_payload["start"] = _normalize_location(request_payload["start"])
    request_payload["finish"] = _normalize_location(request_payload["finish"])
    request_payload["waypoints"] = [
        _normalize_location(value) for value in request_payload["waypoints"]
    ]
    payload = {
        "version": CACHE_SCHEMA_VERSION,
        "market": market.response_metadata(),
        "providers": {
            "stations": market.station_source_slug,
            "geocoding": market.geocoding_source_slug,
            "routing": market.routing_source_slug,
        },
        "request": request_payload,
        "station_snapshot": catalogue.snapshot_version,
        "observation_watermark": catalogue.observation_watermark,
        # Source switches and expiry change resolved quotes without inserting an
        # observation. A warm cache must follow the currently usable evidence.
        "resolved_quotes": [
            {"station": station.stable_id, "quote": asdict(station.price_quote)}
            for station in sorted(catalogue.stations, key=lambda item: item.stable_id)
        ],
        "resolver_version": RESOLVER_VERSION,
        "route_alternatives": settings.ROUTE_ALTERNATIVES,
        "geometry_overview": settings.ROUTE_GEOMETRY_OVERVIEW,
        "time_value_per_hour": str(market.time_value_per_hour),
        "stop_penalty": str(market.stop_penalty),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    digest = hashlib.sha256(encoded.encode()).hexdigest()
    return f"fuelup:{CACHE_SCHEMA_VERSION}:{market.code}:{digest}"


def _cache_ttl(catalogue, market):
    maximum = market.route_cache_seconds
    expiry = catalogue.earliest_quote_expiry
    if expiry is None:
        return maximum
    now = datetime.now(UTC)
    return max(1, min(maximum, int((expiry - now).total_seconds())))


def _normalize_location(value):
    return " ".join(value.strip().casefold().split())
