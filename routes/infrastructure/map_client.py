import hashlib
import json
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

from django.conf import settings
from django.core.cache import cache

from routes.domain.entities import Coordinate, GeocodedLocation
from routes.domain.exceptions import (
    ExternalServiceError,
    LocationNotFoundError,
    RouteNotFoundError,
)

_nominatim_lock = threading.Lock()
_last_nominatim_request = 0.0


class MapClient:
    def geocode(self, query):
        query_hash = hashlib.sha256(query.strip().casefold().encode()).hexdigest()
        cache_key = f"geocode:v1:{query_hash}"
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
                "countrycodes": "us",
                "addressdetails": 1,
            }
        )
        payload = self._nominatim_request(f"/search?{parameters}")
        if not payload:
            raise LocationNotFoundError(
                f'Could not find "{query}" within the United States.'
            )

        result = payload[0]
        address = result.get("address", {})
        if address.get("country_code", "").lower() != "us":
            raise LocationNotFoundError(
                f'Location "{query}" is not within the United States.'
            )

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
        coordinates = (
            f"{start.coordinate.longitude},{start.coordinate.latitude};"
            f"{finish.coordinate.longitude},{finish.coordinate.latitude}"
        )
        parameters = urllib.parse.urlencode(
            {
                "overview": "full",
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
            raise RouteNotFoundError("No drivable route was found between the locations.")
        return payload["routes"]

    def _nominatim_request(self, path):
        global _last_nominatim_request
        with _nominatim_lock:
            elapsed = time.monotonic() - _last_nominatim_request
            if elapsed < 1:
                time.sleep(1 - elapsed)
            payload = self._request(settings.GEOCODING_BASE_URL, path)
            _last_nominatim_request = time.monotonic()
            return payload

    @staticmethod
    def _request(base_url, path):
        request = urllib.request.Request(
            f"{base_url.rstrip('/')}{path}",
            headers={
                "Accept": "application/json",
                "User-Agent": settings.EXTERNAL_API_USER_AGENT,
            },
        )
        try:
            with urllib.request.urlopen(
                request, timeout=settings.EXTERNAL_API_TIMEOUT_SECONDS
            ) as response:
                return json.load(response)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise ExternalServiceError(
                "The map service is temporarily unavailable."
            ) from exc
