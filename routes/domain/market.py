from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class MarketConfig:
    code: str
    country_code: str
    country_name: str
    country_geography_id: str
    currency_code: str
    distance_unit: str
    volume_unit: str
    efficiency_unit: str
    distance_units_per_mile: Decimal
    time_value_per_hour: Decimal
    stop_penalty: Decimal
    route_cache_seconds: int
    station_source_slug: str
    geocoding_source_slug: str
    routing_source_slug: str

    def __post_init__(self):
        object.__setattr__(self, "code", self.code.strip().upper())
        object.__setattr__(self, "country_code", self.country_code.strip().lower())
        object.__setattr__(
            self,
            "currency_code",
            self.currency_code.strip().upper(),
        )
        if len(self.code) != 2 or len(self.country_code) != 2:
            raise ValueError("Market and country codes must contain two letters.")
        if len(self.currency_code) != 3:
            raise ValueError("Currency code must contain three letters.")
        if self.time_value_per_hour < 0 or self.stop_penalty < 0:
            raise ValueError("Route scoring values cannot be negative.")
        if self.distance_units_per_mile <= 0:
            raise ValueError("Distance conversion must be greater than zero.")
        if self.route_cache_seconds <= 0:
            raise ValueError("Route cache lifetime must be greater than zero.")

    def response_metadata(self):
        return {
            "code": self.code,
            "country_code": self.country_code,
            "country_name": self.country_name,
            "currency_code": self.currency_code,
            "distance_unit": self.distance_unit,
            "volume_unit": self.volume_unit,
            "efficiency_unit": self.efficiency_unit,
        }
