from collections import Counter
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from routes.domain.exceptions import (
    FuelPlanNotFoundError,
    InsufficientPriceDataError,
)
from routes.domain.fuel_data import (
    GeographicPrecision,
    PriceLabel,
    PriceQualityPolicy,
    RoutePlanRequest,
    RouteStrategy,
)
from routes.domain.geometry import route_priced_stations
from routes.domain.market import MarketConfig
from routes.domain.vehicle_optimizer import optimize_fuel_purchases
from routes.infrastructure.map_client import MarketMapClient

METERS_PER_MILE = Decimal("1609.344")
SECONDS_PER_HOUR = Decimal("3600")


@dataclass(frozen=True, slots=True)
class RouteEvaluation:
    alternative_number: int
    route: dict
    distance: Decimal
    duration_hours: Decimal
    fuel_plan: object
    selection_score: Decimal


def build_route_plan(
    route_request: RoutePlanRequest,
    *,
    catalogue,
    market: MarketConfig,
    client=None,
):
    client = client or MarketMapClient(market)
    location_queries = (
        route_request.start,
        *route_request.waypoints,
        route_request.finish,
    )
    locations = tuple(client.geocode(query) for query in location_queries)
    routes = client.routes_through(locations)
    stations = _stations_for_quality(catalogue.stations, route_request)

    evaluations = []
    errors = []
    for alternative_number, route in enumerate(routes, start=1):
        try:
            evaluations.append(
                _evaluate_route(
                    alternative_number,
                    route,
                    stations,
                    route_request,
                    market,
                )
            )
        except FuelPlanNotFoundError as exc:
            errors.append(exc)
    if not evaluations:
        if not stations:
            raise InsufficientPriceDataError(
                "No compatible station prices satisfy the requested quality policy."
            )
        raise errors[0] if errors else FuelPlanNotFoundError(
            "No route alternative has enough compatible station coverage."
        )

    selected = min(evaluations, key=lambda item: _selection_key(item, route_request))
    return _serialize_plan(
        route_request=route_request,
        locations=locations,
        selected=selected,
        evaluations=evaluations,
        routes_evaluated=len(routes),
        catalogue=catalogue,
        market=market,
    )


def _evaluate_route(
    alternative_number,
    route,
    stations,
    route_request,
    market,
):
    distance = (
        Decimal(str(route["distance"]))
        / METERS_PER_MILE
        * market.distance_units_per_mile
    )
    duration_hours = Decimal(str(route["duration"])) / SECONDS_PER_HOUR
    candidates = route_priced_stations(
        stations,
        route["geometry"]["coordinates"],
        distance,
        route_request.maximum_detour,
        market.distance_units_per_mile,
    )
    fuel_plan = optimize_fuel_purchases(
        candidates,
        distance,
        route_request.vehicle,
    )
    score = (
        fuel_plan.purchase_cost
        + duration_hours * market.time_value_per_hour
        + Decimal(len(fuel_plan.purchases)) * market.stop_penalty
    )
    return RouteEvaluation(
        alternative_number=alternative_number,
        route=route,
        distance=distance,
        duration_hours=duration_hours,
        fuel_plan=fuel_plan,
        selection_score=_money(score),
    )


def _selection_key(evaluation, route_request):
    if route_request.strategy == RouteStrategy.FASTEST:
        return (
            evaluation.duration_hours,
            evaluation.fuel_plan.purchase_cost,
            evaluation.distance,
        )
    if route_request.strategy == RouteStrategy.CHEAPEST_ESTIMATED:
        return (
            evaluation.fuel_plan.purchase_cost,
            evaluation.duration_hours,
            evaluation.distance,
        )
    return (
        evaluation.selection_score,
        evaluation.fuel_plan.purchase_cost,
        evaluation.duration_hours,
    )


def _stations_for_quality(stations, route_request):
    if route_request.price_quality != PriceQualityPolicy.STATION_REPORTED_ONLY:
        return stations
    return tuple(
        station
        for station in stations
        if station.price_quote.label in {PriceLabel.LIVE, PriceLabel.REPORTED}
        and station.price_quote.geography_precision == GeographicPrecision.STATION
    )


def _serialize_plan(
    *,
    route_request,
    locations,
    selected,
    evaluations,
    routes_evaluated,
    catalogue,
    market,
):
    purchases = selected.fuel_plan.purchases
    route_feature = {
        "type": "Feature",
        "geometry": selected.route["geometry"],
        "properties": {
            "kind": "route",
            "distance": _number(selected.distance),
            "distance_unit": market.distance_unit,
        },
    }
    stop_features = [
        _stop_feature(purchase, index + 1)
        for index, purchase in enumerate(purchases)
    ]
    consumed_volume = selected.distance / route_request.vehicle.efficiency
    return {
        "api_version": "v2",
        "market": market.response_metadata(),
        "start": _location_payload(locations[0]),
        "finish": _location_payload(locations[-1]),
        "waypoints": [_location_payload(location) for location in locations[1:-1]],
        "route": {
            "distance": _number(selected.distance),
            "duration_hours": _number(selected.duration_hours),
            "geojson": {
                "type": "FeatureCollection",
                "features": [route_feature, *stop_features],
            },
        },
        "vehicle": _vehicle_payload(route_request),
        "fuel_plan": {
            "starting_fuel": _number(selected.fuel_plan.starting_fuel),
            "reserve_fuel": _number(selected.fuel_plan.reserve_fuel),
            "stops": [
                _purchase_payload(purchase, index + 1)
                for index, purchase in enumerate(purchases)
            ],
            "total_consumed_volume": _number(consumed_volume),
            "purchased_volume": _number(selected.fuel_plan.purchased_volume),
            "purchase_cost": _number(selected.fuel_plan.purchase_cost),
            "arrival_fuel": _number(selected.fuel_plan.arrival_fuel),
            "currency": market.currency_code,
        },
        "comparisons": [
            _comparison_payload(evaluation, route_request)
            for evaluation in evaluations
        ],
        "data_quality": _data_quality_payload(purchases, catalogue),
        "metadata": {
            "strategy": route_request.strategy.value,
            "price_quality_policy": route_request.price_quality.value,
            "route_alternatives_evaluated": routes_evaluated,
            "feasible_route_alternatives": len(evaluations),
            "selected_alternative": selected.alternative_number,
            "selection_score": _number(selected.selection_score),
            "routing_provider": "OSRM-compatible",
            "geocoding_provider": "OpenStreetMap Nominatim",
            "detour_validation": "estimated",
            "station_attribution": catalogue.attribution,
        },
    }


def _vehicle_payload(route_request):
    vehicle = route_request.vehicle
    return {
        "fuel_type": vehicle.fuel_type.value,
        "fuel_grade": vehicle.fuel_grade,
        "tank_capacity": _number(vehicle.tank_capacity),
        "efficiency": _number(vehicle.efficiency),
        "starting_fuel": _number(vehicle.starting_fuel),
        "reserve_fuel": _number(vehicle.reserve_fuel),
        "maximum_range": _number(vehicle.maximum_range),
        "maximum_station_detour": _number(route_request.maximum_detour),
    }


def _purchase_payload(purchase, sequence):
    candidate = purchase.route_candidate
    station = candidate.station
    quote = station.price_quote
    return {
        "sequence": sequence,
        "station_id": station.stable_id,
        "name": station.name,
        "address": station.address,
        "city": station.city,
        "state": station.state,
        "latitude": station.coordinate.latitude,
        "longitude": station.coordinate.longitude,
        "route_distance": _number(candidate.route_distance),
        "distance_to_route": _number(candidate.distance_to_route),
        "unit_price": _number(quote.unit_price),
        "price": _quote_payload(quote),
        "fuel_on_arrival": _number(purchase.fuel_on_arrival),
        "volume": _number(purchase.volume),
        "cost": _number(purchase.cost),
    }


def _quote_payload(quote):
    return {
        "label": quote.label.value,
        "geographic_precision": (
            quote.geography_precision.value
            if quote.geography_precision is not None
            else None
        ),
        "confidence": quote.confidence.value,
        "as_of": quote.as_of.isoformat() if quote.as_of else None,
        "expires_at": quote.expires_at.isoformat() if quote.expires_at else None,
        "observation_ids": list(quote.observation_ids),
        "resolver_version": quote.resolver_version,
    }


def _comparison_payload(evaluation, route_request):
    return {
        "alternative": evaluation.alternative_number,
        "distance": _number(evaluation.distance),
        "duration_hours": _number(evaluation.duration_hours),
        "fuel_stops": len(evaluation.fuel_plan.purchases),
        "purchase_cost": _number(evaluation.fuel_plan.purchase_cost),
        "selection_score": _number(evaluation.selection_score),
        "requested_strategy": route_request.strategy.value,
    }


def _data_quality_payload(purchases, catalogue):
    quotes = [purchase.route_candidate.station.price_quote for purchase in purchases]
    labels = Counter(quote.label.value for quote in quotes)
    confidences = Counter(quote.confidence.value for quote in quotes)
    as_of_values = [quote.as_of for quote in quotes if quote.as_of]
    return {
        "station_snapshot": catalogue.snapshot_version,
        "station_snapshot_generated_at": (
            catalogue.snapshot_generated_at.isoformat()
            if catalogue.snapshot_generated_at
            else None
        ),
        "observation_watermark": catalogue.observation_watermark,
        "required_stop_quotes": len(quotes),
        "resolved_stop_quotes": len(quotes),
        "price_coverage_percent": 100 if quotes or not purchases else 0,
        "label_counts": dict(sorted(labels.items())),
        "confidence_counts": dict(sorted(confidences.items())),
        "oldest_price_as_of": (
            min(as_of_values).isoformat() if as_of_values else None
        ),
        "warning": (
            "Fuel stop prices are estimates or reports, not a guaranteed "
            "current pump price."
            if quotes
            else "No fuel purchase is required for this plan."
        ),
    }


def _location_payload(location):
    return {
        "query": location.query,
        "display_name": location.display_name,
        "latitude": location.coordinate.latitude,
        "longitude": location.coordinate.longitude,
    }


def _stop_feature(purchase, sequence):
    station = purchase.route_candidate.station
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
            "unit_price": _number(station.price_quote.unit_price),
            "price_label": station.price_quote.label.value,
        },
    }


def _money(value):
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _number(value):
    return float(
        Decimal(str(value)).quantize(
            Decimal("0.001"),
            rounding=ROUND_HALF_UP,
        )
    )
