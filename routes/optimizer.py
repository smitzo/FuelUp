from decimal import Decimal, ROUND_HALF_UP

from routes.exceptions import FuelPlanNotFoundError
from routes.types import FuelPurchase, OptimizedFuelPlan

MAX_RANGE_MILES = 500.0
MILES_PER_GALLON = 10.0
TANK_GALLONS = MAX_RANGE_MILES / MILES_PER_GALLON
STOP_PENALTY_USD = Decimal("8.00")


def optimize_fuel_purchases(candidates, route_distance_miles):
    candidates = [
        candidate
        for candidate in candidates
        if 0 <= candidate.route_mile <= route_distance_miles
    ]
    if not candidates:
        raise FuelPlanNotFoundError("No fuel stations were found near this route.")

    costs = [None] * len(candidates)
    previous = [None] * len(candidates)

    for index, candidate in enumerate(candidates):
        route_mile = candidate.route_mile
        if route_mile <= MAX_RANGE_MILES:
            costs[index] = (
                Decimal(str(route_mile / MILES_PER_GALLON))
                * candidate.station.retail_price
                + STOP_PENALTY_USD
            )

        for prior_index in range(index - 1, -1, -1):
            prior = candidates[prior_index]
            gap = route_mile - prior.route_mile
            if gap > MAX_RANGE_MILES:
                break
            if costs[prior_index] is None or gap <= 0:
                continue
            option = (
                costs[prior_index]
                + Decimal(str(gap / MILES_PER_GALLON))
                * prior.station.retail_price
                + STOP_PENALTY_USD
            )
            if costs[index] is None or option < costs[index]:
                costs[index] = option
                previous[index] = prior_index

    best_index = None
    best_cost = None
    for index, candidate in enumerate(candidates):
        destination_gap = route_distance_miles - candidate.route_mile
        if (
            costs[index] is None
            or destination_gap < 0
            or destination_gap > MAX_RANGE_MILES
        ):
            continue
        option = costs[index] + (
            Decimal(str(destination_gap / MILES_PER_GALLON))
            * candidate.station.retail_price
        )
        if best_cost is None or option < best_cost:
            best_cost = option
            best_index = index

    if best_index is None:
        raise FuelPlanNotFoundError(
            "The station data contains a gap greater than the vehicle's "
            "500-mile range along this route."
        )

    selected = []
    index = best_index
    while index is not None:
        selected.append(candidates[index])
        index = previous[index]
    selected.reverse()

    first = selected[0]
    initial_gallons = first.route_mile / MILES_PER_GALLON
    initial_fuel = FuelPurchase(
        route_station=first,
        gallons=initial_gallons,
        cost=_money(Decimal(str(initial_gallons)) * first.station.retail_price),
        fuel_on_arrival_gallons=0,
    )

    purchases = []
    for position, candidate in enumerate(selected):
        next_mile = (
            selected[position + 1].route_mile
            if position + 1 < len(selected)
            else route_distance_miles
        )
        gallons = (next_mile - candidate.route_mile) / MILES_PER_GALLON
        if gallons <= 0.001:
            continue
        purchases.append(
            FuelPurchase(
                route_station=candidate,
                gallons=gallons,
                cost=_money(
                    Decimal(str(gallons)) * candidate.station.retail_price
                ),
                fuel_on_arrival_gallons=0,
            )
        )

    return OptimizedFuelPlan(
        initial_fuel=initial_fuel,
        purchases=tuple(purchases),
    )


def _money(value):
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
