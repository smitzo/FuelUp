from decimal import Decimal

from routes.clients import MapClient
from routes.geometry import route_stations
from routes.optimizer import MILES_PER_GALLON, optimize_fuel_purchases
from routes.stations import load_stations

METERS_PER_MILE = 1609.344
SECONDS_PER_HOUR = 3600


def build_route_plan(start_query, finish_query, client=None):
    client = client or MapClient()
    start = client.geocode(start_query)
    finish = client.geocode(finish_query)
    route = client.route(start, finish)
    distance_miles = route["distance"] / METERS_PER_MILE
    duration_hours = route["duration"] / SECONDS_PER_HOUR
    coordinates = route["geometry"]["coordinates"]
    candidates = route_stations(load_stations(), coordinates, distance_miles)
    fuel_plan = optimize_fuel_purchases(candidates, distance_miles)
    purchases = fuel_plan.purchases
    total_cost = fuel_plan.initial_fuel.cost + sum(
        (purchase.cost for purchase in purchases), Decimal("0.00")
    )

    stop_features = [_stop_feature(purchase, index + 1) for index, purchase in enumerate(purchases)]
    route_feature = {
        "type": "Feature",
        "geometry": route["geometry"],
        "properties": {"kind": "route", "distance_miles": round(distance_miles, 2)},
    }

    return {
        "start": _location_payload(start),
        "finish": _location_payload(finish),
        "route": {
            "distance_miles": round(distance_miles, 2),
            "duration_hours": round(duration_hours, 2),
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
            "initial_fuel_estimate": _initial_fuel_payload(fuel_plan.initial_fuel),
            "stops": [
                _purchase_payload(purchase, index + 1)
                for index, purchase in enumerate(purchases)
            ],
            "total_gallons": round(distance_miles / MILES_PER_GALLON, 2),
            "total_cost_usd": float(total_cost),
            "currency": "USD",
        },
        "metadata": {
            "external_calls": "Up to two cached geocoding calls and one routing call.",
            "routing_provider": "OSRM public demo server",
            "geocoding_provider": "OpenStreetMap Nominatim",
            "station_coordinate_accuracy": "Approximate city/postal locality",
            "assumption": (
                "Fuel used before the first stop is priced using that station as "
                "the nearest available price reference. Stop selection minimizes "
                "fuel cost plus an $8 operational penalty per stop, preventing "
                "impractical detours for tiny price differences."
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
