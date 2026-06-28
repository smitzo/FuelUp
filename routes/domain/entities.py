from dataclasses import dataclass
from decimal import Decimal

from routes.domain.fuel_data import (
    FuelType,
    OperatingStatus,
    ResolvedPriceQuote,
)


@dataclass(frozen=True, slots=True)
class Coordinate:
    latitude: float
    longitude: float


@dataclass(frozen=True, slots=True)
class GeocodedLocation:
    query: str
    display_name: str
    coordinate: Coordinate


@dataclass(frozen=True, slots=True)
class Station:
    opis_id: str
    name: str
    address: str
    city: str
    state: str
    retail_price: Decimal
    coordinate: Coordinate


@dataclass(frozen=True, slots=True)
class RouteStation:
    station: Station
    route_mile: float
    distance_to_route_miles: float


@dataclass(frozen=True, slots=True)
class FuelPurchase:
    route_station: RouteStation
    gallons: float
    cost: Decimal
    fuel_on_arrival_gallons: float


@dataclass(frozen=True, slots=True)
class OptimizedFuelPlan:
    initial_fuel: FuelPurchase
    purchases: tuple[FuelPurchase, ...]


@dataclass(frozen=True, slots=True)
class PricedStation:
    stable_id: str
    name: str
    address: str
    city: str
    state: str
    coordinate: Coordinate
    fuel_types: frozenset[FuelType]
    price_quote: ResolvedPriceQuote
    operating_status: OperatingStatus = OperatingStatus.UNKNOWN


@dataclass(frozen=True, slots=True)
class RouteCandidate:
    station: PricedStation
    route_distance: float
    distance_to_route: float


@dataclass(frozen=True, slots=True)
class PlannedFuelPurchase:
    route_candidate: RouteCandidate
    volume: Decimal
    cost: Decimal
    fuel_on_arrival: Decimal


@dataclass(frozen=True, slots=True)
class OptimizedVehiclePlan:
    starting_fuel: Decimal
    reserve_fuel: Decimal
    purchases: tuple[PlannedFuelPurchase, ...]
    arrival_fuel: Decimal

    @property
    def purchase_cost(self):
        return sum(
            (purchase.cost for purchase in self.purchases),
            Decimal("0.00"),
        )

    @property
    def purchased_volume(self):
        return sum(
            (purchase.volume for purchase in self.purchases),
            Decimal("0.000"),
        )
