from datetime import timedelta
from decimal import Decimal

from django.test import SimpleTestCase
from django.utils import timezone

from routes.domain.entities import Coordinate, PricedStation, RouteCandidate
from routes.domain.exceptions import FuelPlanNotFoundError
from routes.domain.fuel_data import (
    Confidence,
    FuelType,
    GeographicPrecision,
    PriceLabel,
    ResolvedPriceQuote,
    VehicleProfile,
)
from routes.domain.vehicle_optimizer import optimize_fuel_purchases


class VehicleFuelOptimizerTests(SimpleTestCase):
    def setUp(self):
        self.vehicle = VehicleProfile(
            fuel_type=FuelType.PETROL,
            tank_capacity=Decimal("35"),
            efficiency=Decimal("18"),
            starting_fuel=Decimal("8"),
            reserve_fuel=Decimal("3"),
        )

    def test_uses_starting_fuel_then_buys_to_first_cheaper_station(self):
        plan = optimize_fuel_purchases(
            [
                _candidate(100, "105.00"),
                _candidate(300, "95.00"),
            ],
            500,
            self.vehicle,
        )

        self.assertEqual(
            [purchase.route_candidate.route_distance for purchase in plan.purchases],
            [100, 300],
        )
        self.assertEqual(plan.purchases[0].volume, Decimal("8.667"))
        self.assertEqual(plan.purchases[1].volume, Decimal("11.111"))
        self.assertEqual(plan.reserve_fuel, Decimal("3"))
        self.assertEqual(plan.arrival_fuel, Decimal("0"))

    def test_needs_no_purchase_when_starting_fuel_reaches_destination(self):
        plan = optimize_fuel_purchases([], 100, self.vehicle)

        self.assertEqual(plan.purchases, ())
        self.assertEqual(
            plan.arrival_fuel.quantize(Decimal("0.001")),
            Decimal("2.444"),
        )

    def test_excludes_station_with_wrong_fuel_type(self):
        with self.assertRaisesRegex(FuelPlanNotFoundError, "No compatible"):
            optimize_fuel_purchases(
                [_candidate(100, "90", fuel_type=FuelType.DIESEL)],
                500,
                self.vehicle,
            )

    def test_rejects_first_station_beyond_starting_fuel_range(self):
        with self.assertRaisesRegex(FuelPlanNotFoundError, "starting fuel"):
            optimize_fuel_purchases(
                [_candidate(200, "100")],
                500,
                self.vehicle,
            )

    def test_rejects_gap_beyond_usable_tank_range(self):
        with self.assertRaisesRegex(FuelPlanNotFoundError, "usable range"):
            optimize_fuel_purchases(
                [_candidate(100, "100"), _candidate(700, "95")],
                900,
                self.vehicle,
            )

    def test_decimal_cost_is_deterministic(self):
        candidates = [_candidate(100, "101.237"), _candidate(400, "98.123")]

        first = optimize_fuel_purchases(candidates, 500, self.vehicle)
        second = optimize_fuel_purchases(candidates, 500, self.vehicle)

        self.assertEqual(first, second)
        self.assertEqual(first.purchase_cost.as_tuple().exponent, -2)


def _candidate(route_distance, price, fuel_type=FuelType.PETROL):
    now = timezone.now()
    quote = ResolvedPriceQuote(
        unit_price=Decimal(price),
        label=PriceLabel.REPORTED,
        geography_precision=GeographicPrecision.STATION,
        confidence=Confidence.MEDIUM,
        as_of=now,
        expires_at=now + timedelta(hours=24),
        observation_ids=(f"observation-{route_distance}",),
    )
    station = PricedStation(
        stable_id=f"osm-node-{route_distance}",
        name=f"Fuel station {route_distance}",
        address="Test Road",
        city="Test City",
        state="Gujarat",
        coordinate=Coordinate(23, 72),
        fuel_types=frozenset({fuel_type}),
        price_quote=quote,
    )
    return RouteCandidate(
        station=station,
        route_distance=route_distance,
        distance_to_route=Decimal("1"),
    )
