from decimal import ROUND_HALF_UP, Decimal

from routes.domain.entities import (
    OptimizedVehiclePlan,
    PlannedFuelPurchase,
    RouteCandidate,
)
from routes.domain.exceptions import FuelPlanNotFoundError
from routes.domain.fuel_data import VehicleProfile

POSITION_EPSILON = Decimal("0.1")
PURCHASE_EPSILON = Decimal("0.001")


def optimize_fuel_purchases(candidates, route_distance, vehicle: VehicleProfile):
    route_distance = _decimal(route_distance)
    stations = _prepare_candidates(candidates, route_distance, vehicle)
    _validate_route_coverage(stations, route_distance, vehicle)

    fuel = vehicle.starting_fuel
    purchases = []
    current_distance = Decimal("0")
    for index, station in enumerate(stations):
        fuel = _consume_fuel(
            fuel,
            _decimal(station.route_distance) - current_distance,
            vehicle,
        )
        current_distance = _decimal(station.route_distance)
        purchase = _purchase_at_station(
            current=station,
            current_distance=current_distance,
            fuel=fuel,
            future_stations=stations[index + 1 :],
            route_distance=route_distance,
            vehicle=vehicle,
        )
        if purchase.volume > PURCHASE_EPSILON:
            purchases.append(purchase)
            fuel += purchase.volume

    arrival_fuel = _consume_fuel(
        fuel,
        route_distance - current_distance,
        vehicle,
    )
    return OptimizedVehiclePlan(
        starting_fuel=vehicle.starting_fuel,
        reserve_fuel=vehicle.reserve_fuel,
        purchases=tuple(purchases),
        arrival_fuel=_volume(arrival_fuel),
    )


def _prepare_candidates(candidates, route_distance, vehicle):
    compatible = sorted(
        (
            candidate
            for candidate in candidates
            if _is_compatible(candidate, vehicle)
            and Decimal("0")
            < _decimal(candidate.route_distance)
            < route_distance
        ),
        key=lambda candidate: (
            _decimal(candidate.route_distance),
            _station_price(candidate),
            _decimal(candidate.distance_to_route),
            candidate.station.stable_id,
        ),
    )
    prepared = []
    for candidate in compatible:
        if (
            prepared
            and _decimal(candidate.route_distance)
            - _decimal(prepared[-1].route_distance)
            < POSITION_EPSILON
        ):
            if _station_rank(candidate) < _station_rank(prepared[-1]):
                prepared[-1] = candidate
            continue
        prepared.append(candidate)
    return tuple(prepared)


def _is_compatible(candidate, vehicle):
    quote = candidate.station.price_quote
    return (
        quote.unit_price is not None
        and vehicle.fuel_type in candidate.station.fuel_types
    )


def _validate_route_coverage(stations, route_distance, vehicle):
    start_range = vehicle.starting_fuel * vehicle.efficiency
    if route_distance <= start_range:
        return
    if not stations:
        raise FuelPlanNotFoundError(
            "No compatible priced fuel station is reachable on this route."
        )
    first_distance = _decimal(stations[0].route_distance)
    if first_distance > start_range + POSITION_EPSILON:
        raise FuelPlanNotFoundError(
            "The first compatible station is beyond the vehicle's starting fuel range."
        )

    positions = [
        *(_decimal(station.route_distance) for station in stations),
        route_distance,
    ]
    for start, finish in zip(positions, positions[1:], strict=False):
        if finish - start > vehicle.maximum_range + POSITION_EPSILON:
            raise FuelPlanNotFoundError(
                "The route has a compatible-station gap beyond the vehicle's "
                "usable range."
            )


def _purchase_at_station(
    *,
    current,
    current_distance,
    fuel,
    future_stations,
    route_distance,
    vehicle,
):
    target_distance = _next_purchase_target(
        current_distance=current_distance,
        current_price=_station_price(current),
        future_stations=future_stations,
        route_distance=route_distance,
        maximum_range=vehicle.maximum_range,
    )
    desired_fuel = (
        (target_distance - current_distance) / vehicle.efficiency
        if target_distance is not None
        else vehicle.usable_capacity
    )
    volume = max(
        Decimal("0"),
        min(vehicle.usable_capacity, desired_fuel) - fuel,
    )
    return PlannedFuelPurchase(
        route_candidate=current,
        volume=_volume(volume),
        cost=_money(volume * _station_price(current)),
        fuel_on_arrival=_volume(max(Decimal("0"), fuel)),
    )


def _next_purchase_target(
    *,
    current_distance,
    current_price,
    future_stations,
    route_distance,
    maximum_range,
):
    furthest_equal_distance = None
    for station in future_stations:
        station_distance = _decimal(station.route_distance)
        distance = station_distance - current_distance
        if distance > maximum_range:
            break
        price = _station_price(station)
        if price < current_price:
            return station_distance
        if price == current_price:
            furthest_equal_distance = station_distance
    if route_distance - current_distance <= maximum_range:
        return route_distance
    return furthest_equal_distance


def _consume_fuel(fuel, distance, vehicle):
    required = max(Decimal("0"), distance) / vehicle.efficiency
    remaining = fuel - required
    if remaining < -PURCHASE_EPSILON:
        raise FuelPlanNotFoundError(
            "The generated fuel plan cannot cover the next route segment."
        )
    return max(Decimal("0"), remaining)


def _station_price(candidate: RouteCandidate):
    price = candidate.station.price_quote.unit_price
    if price is None:
        raise FuelPlanNotFoundError("A selected station has no usable price quote.")
    return price


def _station_rank(candidate):
    return (
        _station_price(candidate),
        _decimal(candidate.distance_to_route),
        _decimal(candidate.route_distance),
        candidate.station.stable_id,
    )


def _decimal(value):
    return value if isinstance(value, Decimal) else Decimal(str(value))


def _money(value):
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _volume(value):
    return value.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
