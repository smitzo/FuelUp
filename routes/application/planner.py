from dataclasses import dataclass
from decimal import Decimal

from django.conf import settings

from routes.domain.exceptions import FuelPlanNotFoundError
from routes.domain.geometry import route_stations
from routes.domain.optimizer import MILES_PER_GALLON, optimize_fuel_purchases
from routes.infrastructure.map_client import MapClient
from routes.infrastructure.station_repository import load_stations

METERS_PER_MILE = 1609.344
SECONDS_PER_HOUR = 3600


@dataclass(frozen=True, slots=True)
class RouteEvaluation:
    route: dict
    distance_miles: float
    duration_hours: float
    fuel_plan: object
    total_fuel_cost: Decimal
    selection_score: Decimal


def build_route_plan(start_query, finish_query, client=None):
    client = client or MapClient()
    start = client.geocode(start_query)
    finish = client.geocode(finish_query)
    routes = client.routes(start, finish)
    stations = load_stations()

    evaluations = []
    errors = []
    for route in routes:
        try:
            evaluations.append(_evaluate_route(route, stations))
        except FuelPlanNotFoundError as exc:
            errors.append(exc)
    if not evaluations:
        raise errors[0] if errors else FuelPlanNotFoundError(
            "No route alternative has enough station coverage."
        )

    selected = min(
        evaluations,
        key=lambda evaluation: (
            evaluation.selection_score,
            evaluation.total_fuel_cost,
            evaluation.duration_hours,
        ),
    )
    return _serialize_plan(
        start=start,
        finish=finish,
        selected=selected,
        alternatives_evaluated=len(routes),
        feasible_alternatives=len(evaluations),
    )


def _evaluate_route(route, stations):
    distance_miles = route["distance"] / METERS_PER_MILE
    duration_hours = route["duration"] / SECONDS_PER_HOUR
    candidates = route_stations(
        stations,
        route["geometry"]["coordinates"],
        distance_miles,
    )
    fuel_plan = optimize_fuel_purchases(candidates, distance_miles)
    total_fuel_cost = fuel_plan.initial_fuel.cost + sum(
        (purchase.cost for purchase in fuel_plan.purchases),
        Decimal("0.00"),
    )
    selection_score = (
        total_fuel_cost
        + Decimal(str(duration_hours * settings.ROUTE_TIME_VALUE_USD_PER_HOUR))
        + Decimal(
            str(len(fuel_plan.purchases) * settings.ROUTE_STOP_PENALTY_USD)
        )
    )
    return RouteEvaluation(
        route=route,
        distance_miles=distance_miles,
        duration_hours=duration_hours,
        fuel_plan=fuel_plan,
        total_fuel_cost=total_fuel_cost,
        selection_score=selection_score,
    )


def _serialize_plan(
    *,
    start,
    finish,
    selected,
    alternatives_evaluated,
    feasible_alternatives,
):
    purchases = selected.fuel_plan.purchases
    stop_features = [
        _stop_feature(purchase, index + 1)
        for index, purchase in enumerate(purchases)
    ]
    route_feature = {
        "type": "Feature",
        "geometry": selected.route["geometry"],
        "properties": {
            "kind": "route",
            "distance_miles": round(selected.distance_miles, 2),
        },
    }
    return {
        "start": _location_payload(start),
        "finish": _location_payload(finish),
        "route": {
            "distance_miles": round(selected.distance_miles, 2),
            "duration_hours": round(selected.duration_hours, 2),
            "geojson": {
                "type": "FeatureCollection",
                "features": [route_feature, *stop_features],
            },
        },
        "vehicle": {
            "maximum_range_miles": 500,
            "fuel_economy_mpg": MILES_PER_GALLON,
            "tank_capacity_gallons": 50,
        },
        "fuel_plan": {
            "initial_fuel_estimate": _initial_fuel_payload(
                selected.fuel_plan.initial_fuel
            ),
            "stops": [
                _purchase_payload(purchase, index + 1)
                for index, purchase in enumerate(purchases)
            ],
            "total_gallons": round(
                selected.distance_miles / MILES_PER_GALLON, 2
            ),
            "total_cost_usd": float(selected.total_fuel_cost),
            "currency": "USD",
        },
        "metadata": {
            "external_calls": (
                "Up to two cached geocoding calls and one routing call."
            ),
            "routing_provider": "OSRM",
            "geocoding_provider": "OpenStreetMap Nominatim",
            "station_coordinate_accuracy": "Approximate city/postal locality",
            "route_alternatives_evaluated": alternatives_evaluated,
            "feasible_route_alternatives": feasible_alternatives,
            "selection_score_usd": float(selected.selection_score),
            "selection_policy": (
                "Minimum fuel cost plus configured time and stop penalties."
            ),
            "assumption": (
                "Fuel used before the first stop is priced using a nearby "
                "station as the origin price reference. Fuel purchases on a "
                "fixed route are cost-optimal for the configured tank and MPG."
            ),
        },
    }


def _location_payload(location):
    return {
        "query": location.query,
        "display_name": location.display_name,
        "latitude": location.coordinate.latitude,
        "longitude": location.coordinate.longitude,
    }


def _purchase_payload(purchase, sequence):
    candidate = purchase.route_station
    station = candidate.station
    return {
        "sequence": sequence,
        "opis_id": station.opis_id,
        "name": station.name,
        "address": station.address,
        "city": station.city,
        "state": station.state,
        "latitude": station.coordinate.latitude,
        "longitude": station.coordinate.longitude,
        "route_mile": round(candidate.route_mile, 2),
        "distance_to_route_miles": round(candidate.distance_to_route_miles, 2),
        "price_per_gallon_usd": float(station.retail_price),
        "fuel_on_arrival_gallons": round(
            purchase.fuel_on_arrival_gallons, 2
        ),
        "gallons": round(purchase.gallons, 2),
        "cost_usd": float(purchase.cost),
    }


def _initial_fuel_payload(purchase):
    station = purchase.route_station.station
    return {
        "gallons": round(purchase.gallons, 2),
        "cost_usd": float(purchase.cost),
        "price_reference": {
            "opis_id": station.opis_id,
            "name": station.name,
            "city": station.city,
            "state": station.state,
            "price_per_gallon_usd": float(station.retail_price),
        },
    }


def _stop_feature(purchase, sequence):
    station = purchase.route_station.station
    return {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [
                station.coordinate.longitude,
                station.coordinate.latitude,
            ],
        },
        "properties": {
            "kind": "fuel_stop",
            "sequence": sequence,
            "name": station.name,
            "price_per_gallon_usd": float(station.retail_price),
        },
    }
