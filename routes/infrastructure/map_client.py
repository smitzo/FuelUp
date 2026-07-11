import hashlib
import json
import logging
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from time import perf_counter

from django.conf import settings
from django.core.cache import cache

from routes.domain.entities import Coordinate, GeocodedLocation
from routes.domain.exceptions import (
    ExternalServiceError,
    LocationNotFoundError,
    RouteNotFoundError,
    UnsupportedCountryError,
)
from routes.domain.market import MarketConfig

_nominatim_lock = threading.Lock()
_last_nominatim_request = 0.0
logger = logging.getLogger("fuelup.providers")
NOMINATIM_INTERVAL_SECONDS = 1.1
NOMINATIM_LOCK_SECONDS = 10


class MapClient:
    country_code = "us"
    country_name = "the United States"

    def geocode(self, query):
        query_hash = hashlib.sha256(
            f"{self.country_code}:{query.strip().casefold()}".encode()
        ).hexdigest()
        cache_key = f"geocode:v2:{query_hash}"
        cached = cache.get(cache_key)
        if cached:
            return GeocodedLocation(
                query=query,
                display_name=cached["display_name"],
                coordinate=Coordinate(
                    latitude=cached["latitude"],
                    longitude=cached["longitude"],
                ),
            )

        parameters = urllib.parse.urlencode(
            {
                "q": query,
                "format": "jsonv2",
                "limit": 1,
                "countrycodes": self.country_code,
                "addressdetails": 1,
            }
        )
        payload = self._nominatim_request(f"/search?{parameters}")
        if not payload:
            raise LocationNotFoundError(
                f'Could not find "{query}" within {self.country_name}.'
            )

        result = payload[0]
        address = result.get("address", {})
        if address.get("country_code", "").lower() != self.country_code:
            self._raise_unsupported_country(query)

        location = GeocodedLocation(
            query=query,
            display_name=result["display_name"],
            coordinate=Coordinate(
                latitude=float(result["lat"]),
                longitude=float(result["lon"]),
            ),
        )
        cache.set(
            cache_key,
            {
                "display_name": location.display_name,
                "latitude": location.coordinate.latitude,
                "longitude": location.coordinate.longitude,
            },
            settings.GEOCODE_CACHE_SECONDS,
        )
        return location

    def routes(self, start, finish):
        return self.routes_through((start, finish))

    def routes_through(self, locations):
        coordinates = ";".join(
            f"{location.coordinate.longitude},{location.coordinate.latitude}"
            for location in locations
        )
        parameters = urllib.parse.urlencode(
            {
                "overview": settings.ROUTE_GEOMETRY_OVERVIEW,
                "geometries": "geojson",
                "steps": "false",
                "alternatives": settings.ROUTE_ALTERNATIVES,
            }
        )
        payload = self._request(
            settings.ROUTING_BASE_URL,
            f"/route/v1/driving/{coordinates}?{parameters}",
        )
        if payload.get("code") != "Ok" or not payload.get("routes"):
            raise RouteNotFoundError(
                "No drivable route was found between the locations."
            )
        return payload["routes"]

    def _raise_unsupported_country(self, query):
        raise LocationNotFoundError(
            f'Location "{query}" is not within {self.country_name}.'
        )

    def _nominatim_request(self, path):
        global _last_nominatim_request
        with _nominatim_lock:
            lock_token = _acquire_distributed_nominatim_lock()
            try:
                _wait_for_nominatim_slot()
                payload = self._request(settings.GEOCODING_BASE_URL, path)
                _last_nominatim_request = time.monotonic()
                try:
                    cache.set(
                        "fuelup:nominatim:last-request",
                        time.time(),
                        timeout=60,
                    )
                except Exception:
                    logger.warning(
                        "nominatim_throttle_cache_unavailable",
                        exc_info=True,
                    )
                return payload
            finally:
                _release_distributed_nominatim_lock(lock_token)

    @staticmethod
    def _request(base_url, path):
        request = urllib.request.Request(
            f"{base_url.rstrip('/')}{path}",
            headers={
                "Accept": "application/json",
                "User-Agent": settings.EXTERNAL_API_USER_AGENT,
            },
        )
        started = perf_counter()
        provider = urllib.parse.urlparse(base_url).netloc
        try:
            with urllib.request.urlopen(
                request, timeout=settings.EXTERNAL_API_TIMEOUT_SECONDS
            ) as response:
                payload = json.load(response)
                logger.info(
                    "provider_request_complete",
                    extra={
                        "provider": provider,
                        "status_code": response.status,
                        "duration_ms": round(
                            (perf_counter() - started) * 1000, 2
                        ),
                    },
                )
                return payload
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            logger.warning(
                "provider_request_failed",
                extra={
                    "provider": provider,
                    "duration_ms": round(
                        (perf_counter() - started) * 1000, 2
                    ),
                },
                exc_info=True,
            )
            raise ExternalServiceError(
                "The map service is temporarily unavailable."
            ) from exc


def _acquire_distributed_nominatim_lock():
    token = uuid.uuid4().hex
    deadline = time.monotonic() + settings.EXTERNAL_API_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        try:
            acquired = cache.add(
                "fuelup:nominatim:lock",
                token,
                timeout=NOMINATIM_LOCK_SECONDS,
            )
        except Exception:
            return None
        if acquired:
            return token
        if acquired is None:
            return None
        time.sleep(0.05)
    return None


def _release_distributed_nominatim_lock(token):
    if token is None:
        return
    try:
        if cache.get("fuelup:nominatim:lock") == token:
            cache.delete("fuelup:nominatim:lock")
    except Exception:
        logger.warning("nominatim_lock_release_failed", exc_info=True)


def _wait_for_nominatim_slot():
    local_wait = NOMINATIM_INTERVAL_SECONDS - (
        time.monotonic() - _last_nominatim_request
    )
    try:
        last_request = cache.get("fuelup:nominatim:last-request")
    except Exception:
        last_request = None
    distributed_wait = (
        NOMINATIM_INTERVAL_SECONDS - (time.time() - last_request)
        if isinstance(last_request, (int, float))
        else 0.0
    )
    wait_seconds = max(local_wait, distributed_wait, 0.0)
    if wait_seconds:
        time.sleep(wait_seconds)


class MarketMapClient(MapClient):
    def __init__(self, market: MarketConfig):
        self.market = market
        self.country_code = market.country_code
        self.country_name = market.country_name

    def geocode(self, query):
        _require_source_enabled(self.market.geocoding_source_slug)
        return super().geocode(query)

    def routes_through(self, locations):
        _require_source_enabled(self.market.routing_source_slug)
        return super().routes_through(locations)

    def _raise_unsupported_country(self, query):
        raise UnsupportedCountryError(
            f'Location "{query}" is outside {self.country_name}, '
            "the current launch market."
        )


def _require_source_enabled(slug):
    from routes.models import SourceRegistry

    source = SourceRegistry.objects.filter(slug=slug).first()
    if source is None or not source.can_fetch:
        raise ExternalServiceError(
            f'The configured provider "{slug}" is disabled by the source registry.'
        )
