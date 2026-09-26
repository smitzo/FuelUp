import math

from django.conf import settings

from routes.domain.exceptions import ExternalServiceError, RouteNotFoundError
from routes.infrastructure.provider_http import request_json

SOURCE_SLUG = "heigit-openrouteservice"


class HeiGitRoutingClient:
    def routes_through(self, locations):
        if not settings.HEIGIT_API_KEY:
            raise ExternalServiceError("Routing provider key is not configured.")
        locations = tuple(locations)
        if not 2 <= len(locations) <= 7:
            raise RouteNotFoundError("Routing supports two to seven locations.")
        payload = {
            "coordinates": [
                [item.coordinate.longitude, item.coordinate.latitude]
                for item in locations
            ],
            "instructions": False,
            "options": {"avoid_borders": "all"},
        }
        # Hosted ORS alternatives are only available for a two-point request.
        if len(locations) == 2 and settings.ROUTE_ALTERNATIVES > 1:
            payload["alternative_routes"] = {
                "target_count": min(settings.ROUTE_ALTERNATIVES, 3),
            }
        result = request_json(
            SOURCE_SLUG,
            settings.HEIGIT_BASE_URL,
            "/v2/directions/driving-car/geojson",
            headers={"Authorization": settings.HEIGIT_API_KEY},
            payload=payload,
        )
        try:
            features = result["features"]
            if not features:
                raise RouteNotFoundError("No drivable route was found.")
            return [_normalize_feature(feature) for feature in features]
        except (KeyError, TypeError, ValueError, OverflowError) as exc:
            raise ExternalServiceError(
                "Routing provider returned invalid route data."
            ) from exc


def _normalize_feature(feature):
    summary = feature["properties"]["summary"]
    geometry = feature["geometry"]
    if geometry["type"] != "LineString" or len(geometry["coordinates"]) < 2:
        raise ValueError("Expected a route line.")
    coordinates = []
    for position in geometry["coordinates"]:
        longitude, latitude = map(float, position[:2])
        if not (-180 <= longitude <= 180 and -90 <= latitude <= 90):
            raise ValueError("Invalid route coordinate.")
        coordinates.append([longitude, latitude])
    distance, duration = float(summary["distance"]), float(summary["duration"])
    if not all(math.isfinite(value) and value >= 0 for value in (distance, duration)):
        raise ValueError("Invalid route summary.")
    return {
        "distance": distance,
        "duration": duration,
        "geometry": {"type": "LineString", "coordinates": coordinates},
    }
