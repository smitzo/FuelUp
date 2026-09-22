from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum


class FuelType(StrEnum):
    PETROL = "petrol"
    DIESEL = "diesel"


class SourceType(StrEnum):
    OFFICIAL_REFERENCE = "official_reference"
    THIRD_PARTY_REFERENCE = "third_party_reference"
    COMMUNITY_REPORT = "community_report"
    MODEL_ESTIMATE = "model_estimate"
    DEMO = "demo"


class GeographicPrecision(StrEnum):
    STATION = "station"
    CITY = "city"
    DISTRICT = "district"
    STATE = "state"
    COUNTRY = "country"


class ObservationState(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    QUARANTINED = "quarantined"
    REJECTED = "rejected"
    RETRACTED = "retracted"
    SUPERSEDED = "superseded"


class PriceLabel(StrEnum):
    LIVE = "live"
    REPORTED = "reported"
    REFERENCE = "reference"
    ESTIMATED = "estimated"
    STALE = "stale"
    UNAVAILABLE = "unavailable"


class Confidence(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNAVAILABLE = "unavailable"


class OperatingStatus(StrEnum):
    OPEN = "open"
    CLOSED = "closed"
    UNKNOWN = "unknown"


class RouteStrategy(StrEnum):
    CHEAPEST_ESTIMATED = "cheapest_estimated"
    FASTEST = "fastest"
    BALANCED = "balanced"


class PriceQualityPolicy(StrEnum):
    BEST_AVAILABLE = "best_available"
    STATION_REPORTED_ONLY = "station_reported_only"


@dataclass(frozen=True, slots=True)
class VehicleProfile:
    fuel_type: FuelType
    tank_capacity: Decimal
    efficiency: Decimal
    starting_fuel: Decimal
    reserve_fuel: Decimal
    fuel_grade: str | None = None

    def __post_init__(self):
        values = {
            "tank_capacity": self.tank_capacity,
            "efficiency": self.efficiency,
        }
        for name, value in values.items():
            if value <= 0:
                raise ValueError(f"{name} must be greater than zero.")
        if self.tank_capacity > Decimal("300"):
            raise ValueError("tank_capacity must be 300 or fewer.")
        if self.efficiency > Decimal("100"):
            raise ValueError("efficiency must be 100 or fewer.")
        if self.starting_fuel < 0 or self.reserve_fuel < 0:
            raise ValueError("Starting fuel and reserve cannot be negative.")
        if self.starting_fuel + self.reserve_fuel > self.tank_capacity:
            raise ValueError(
                "Starting fuel plus reserve cannot exceed tank capacity."
            )
        if self.fuel_grade is not None:
            normalized_grade = self.fuel_grade.strip()
            if not normalized_grade or len(normalized_grade) > 50:
                raise ValueError("fuel_grade must contain 1 to 50 characters.")
            object.__setattr__(self, "fuel_grade", normalized_grade.casefold())

    @property
    def usable_capacity(self):
        return self.tank_capacity - self.reserve_fuel

    @property
    def maximum_range(self):
        return self.usable_capacity * self.efficiency


@dataclass(frozen=True, slots=True)
class RoutePlanRequest:
    start: str
    finish: str
    waypoints: tuple[str, ...]
    vehicle: VehicleProfile
    maximum_detour: Decimal
    strategy: RouteStrategy = RouteStrategy.BALANCED
    price_quality: PriceQualityPolicy = PriceQualityPolicy.BEST_AVAILABLE
    allow_stale_prices: bool = False

    def __post_init__(self):
        locations = (self.start, *self.waypoints, self.finish)
        if any(
            not location.strip() or len(location) > 300
            for location in locations
        ):
            raise ValueError("Locations must contain 1 to 300 characters.")
        if len(self.waypoints) > 5:
            raise ValueError("At most five waypoints are supported.")
        if not Decimal("0") < self.maximum_detour <= Decimal("50"):
            raise ValueError("maximum_detour must be between 0 and 50.")

    def cache_payload(self):
        return {
            "start": self.start,
            "finish": self.finish,
            "waypoints": list(self.waypoints),
            "vehicle": {
                "fuel_type": self.vehicle.fuel_type.value,
                "fuel_grade": self.vehicle.fuel_grade,
                "tank_capacity": str(self.vehicle.tank_capacity),
                "efficiency": str(self.vehicle.efficiency),
                "starting_fuel": str(self.vehicle.starting_fuel),
                "reserve_fuel": str(self.vehicle.reserve_fuel),
            },
            "maximum_detour": str(self.maximum_detour),
            "strategy": self.strategy.value,
            "price_quality": self.price_quality.value,
            "allow_stale_prices": self.allow_stale_prices,
        }


@dataclass(frozen=True, slots=True)
class PriceObservationValue:
    observation_id: str
    station_id: str | None
    geography_precision: GeographicPrecision
    geography_id: str
    fuel_type: FuelType
    fuel_grade: str | None
    unit_price: Decimal
    source_type: SourceType
    source_id: str
    observed_at: datetime
    effective_at: datetime
    received_at: datetime
    expires_at: datetime
    state: ObservationState = ObservationState.ACCEPTED
    contributor_id: str | None = None

    def __post_init__(self):
        if self.unit_price <= 0:
            raise ValueError("unit_price must be greater than zero.")
        if self.expires_at <= self.observed_at:
            raise ValueError("expires_at must be later than observed_at.")
        for field_name in (
            "observed_at",
            "effective_at",
            "received_at",
            "expires_at",
        ):
            value = getattr(self, field_name)
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError(f"{field_name} must be timezone-aware.")

    def is_current(self, at):
        return self.state == ObservationState.ACCEPTED and at < self.expires_at


@dataclass(frozen=True, slots=True)
class ResolvedPriceQuote:
    unit_price: Decimal | None
    label: PriceLabel
    geography_precision: GeographicPrecision | None
    confidence: Confidence
    as_of: datetime | None
    expires_at: datetime | None
    observation_ids: tuple[str, ...] = ()
    resolver_version: str = "fuel-price:v1"

    @classmethod
    def unavailable(cls):
        return cls(
            unit_price=None,
            label=PriceLabel.UNAVAILABLE,
            geography_precision=None,
            confidence=Confidence.UNAVAILABLE,
            as_of=None,
            expires_at=None,
        )
