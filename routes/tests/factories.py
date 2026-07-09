from decimal import Decimal

from routes.domain.market import MarketConfig


def market_config(**overrides):
    values = {
        "code": "IN",
        "country_code": "in",
        "country_name": "India",
        "country_geography_id": "india",
        "currency_code": "INR",
        "distance_unit": "km",
        "volume_unit": "litre",
        "efficiency_unit": "km/litre",
        "distance_units_per_mile": Decimal("1.609344"),
        "time_value_per_hour": Decimal("300"),
        "stop_penalty": Decimal("150"),
        "route_cache_seconds": 3600,
        "station_source_slug": "geofabrik-india-osm",
        "geocoding_source_slug": "osm-public-nominatim",
        "routing_source_slug": "project-osrm-public-demo",
    }
    values.update(overrides)
    return MarketConfig(**values)
