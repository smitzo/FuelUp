from decimal import Decimal

from django.conf import settings

from routes.domain.market import MarketConfig


def get_market_config():
    config = settings.MARKET_CONFIG
    return MarketConfig(
        code=config["code"],
        country_code=config["country_code"],
        country_name=config["country_name"],
        country_geography_id=config["country_geography_id"],
        currency_code=config["currency_code"],
        distance_unit=config["distance_unit"],
        volume_unit=config["volume_unit"],
        efficiency_unit=config["efficiency_unit"],
        distance_units_per_mile=Decimal(
            str(config["distance_units_per_mile"])
        ),
        time_value_per_hour=Decimal(str(config["time_value_per_hour"])),
        stop_penalty=Decimal(str(config["stop_penalty"])),
        route_cache_seconds=int(config["route_cache_seconds"]),
        station_source_slug=config["station_source_slug"],
        geocoding_source_slug=config["geocoding_source_slug"],
        routing_source_slug=config["routing_source_slug"],
    )
