from dataclasses import dataclass
from decimal import Decimal


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
