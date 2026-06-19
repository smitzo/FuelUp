from decimal import Decimal, ROUND_HALF_UP

from routes.domain.entities import FuelPurchase, OptimizedFuelPlan, RouteStation
from routes.domain.exceptions import FuelPlanNotFoundError

MAX_RANGE_MILES = 500.0
MILES_PER_GALLON = 10.0
TANK_GALLONS = MAX_RANGE_MILES / MILES_PER_GALLON
ORIGIN_PRICE_SEARCH_MILES = 50.0
POSITION_EPSILON_MILES = 0.1
PURCHASE_EPSILON_GALLONS = 0.01


def optimize_fuel_purchases(candidates, route_distance_miles):
    stations = _prepare_candidates(candidates, route_distance_miles)
    price_reference = _origin_price_reference(stations)
    _validate_route_coverage(stations, route_distance_miles)

    fuel_gallons = 0.0
    initial_fuel = _purchase_at_position(
        current=price_reference,
        current_mile=0.0,
        current_price=price_reference.station.retail_price,
        fuel_gallons=fuel_gallons,
        future_stations=stations,
        route_distance_miles=route_distance_miles,
    )
    fuel_gallons += initial_fuel.gallons

    purchases = []
    current_mile = 0.0
    for index, station in enumerate(stations):
        fuel_gallons = _consume_fuel(
            fuel_gallons,
            station.route_mile - current_mile,
        )
        current_mile = station.route_mile

        purchase = _purchase_at_position(
            current=station,
            current_mile=current_mile,
            current_price=station.station.retail_price,
            fuel_gallons=fuel_gallons,
            future_stations=stations[index + 1 :],
            route_distance_miles=route_distance_miles,
        )
        if purchase.gallons > PURCHASE_EPSILON_GALLONS:
            purchases.append(purchase)
            fuel_gallons += purchase.gallons

    _consume_fuel(fuel_gallons, route_distance_miles - current_mile)
    return OptimizedFuelPlan(
        initial_fuel=initial_fuel,
        purchases=tuple(purchases),
    )


def _prepare_candidates(candidates, route_distance_miles):
    ordered = sorted(
        (
            candidate
            for candidate in candidates
            if 0 < candidate.route_mile < route_distance_miles
        ),
        key=lambda candidate: (
            candidate.route_mile,
            candidate.station.retail_price,
            candidate.distance_to_route_miles,
        ),
    )
    if not ordered:
        raise FuelPlanNotFoundError("No fuel stations were found near this route.")

    prepared = []
    for candidate in ordered:
        if (
            prepared
            and candidate.route_mile - prepared[-1].route_mile
            < POSITION_EPSILON_MILES
        ):
            if _station_rank(candidate) < _station_rank(prepared[-1]):
                prepared[-1] = candidate
            continue
        prepared.append(candidate)
    return tuple(prepared)


def _origin_price_reference(stations):
    nearby = [
        station
        for station in stations
        if station.route_mile <= ORIGIN_PRICE_SEARCH_MILES
    ]
    candidates = nearby or [
        station for station in stations if station.route_mile <= MAX_RANGE_MILES
    ]
    if not candidates:
        raise FuelPlanNotFoundError(
            "No station is reachable within the vehicle's 500-mile range."
        )
    return min(candidates, key=_station_rank)


def _validate_route_coverage(stations, route_distance_miles):
    positions = [0.0, *(station.route_mile for station in stations), route_distance_miles]
    for start, finish in zip(positions, positions[1:]):
        if finish - start > MAX_RANGE_MILES + POSITION_EPSILON_MILES:
            raise FuelPlanNotFoundError(
                "The station data contains a gap greater than the vehicle's "
                "500-mile range along this route."
            )


def _purchase_at_position(
    *,
    current,
    current_mile,
    current_price,
    fuel_gallons,
    future_stations,
    route_distance_miles,
):
    cheaper_mile = _first_cheaper_mile(
        current_mile=current_mile,
        current_price=current_price,
        future_stations=future_stations,
        route_distance_miles=route_distance_miles,
    )
    desired_fuel = (
        (cheaper_mile - current_mile) / MILES_PER_GALLON
        if cheaper_mile is not None
        else TANK_GALLONS
    )
    gallons = max(0.0, min(TANK_GALLONS, desired_fuel) - fuel_gallons)
    return FuelPurchase(
        route_station=current,
        gallons=gallons,
        cost=_money(Decimal(str(gallons)) * current_price),
        fuel_on_arrival_gallons=max(0.0, fuel_gallons),
    )


def _first_cheaper_mile(
    *,
    current_mile,
    current_price,
    future_stations,
    route_distance_miles,
):
    if route_distance_miles - current_mile <= MAX_RANGE_MILES:
        destination = route_distance_miles
    else:
        destination = None

    for station in future_stations:
        distance = station.route_mile - current_mile
        if distance > MAX_RANGE_MILES:
            break
        if station.station.retail_price < current_price:
            return station.route_mile
    return destination


def _consume_fuel(fuel_gallons, distance_miles):
    required = max(0.0, distance_miles) / MILES_PER_GALLON
    remaining = fuel_gallons - required
    if remaining < -PURCHASE_EPSILON_GALLONS:
        raise FuelPlanNotFoundError(
            "The generated fuel plan cannot cover the next route segment."
        )
    return max(0.0, remaining)


def _station_rank(candidate: RouteStation):
    return (
        candidate.station.retail_price,
        candidate.distance_to_route_miles,
        candidate.route_mile,
        candidate.station.opis_id,
    )


def _money(value):
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
