from decimal import Decimal

from django.test import SimpleTestCase

from routes.domain.entities import Coordinate, RouteStation, Station
from routes.domain.exceptions import FuelPlanNotFoundError
from routes.domain.optimizer import MAX_RANGE_MILES, optimize_fuel_purchases


class FuelOptimizerTests(SimpleTestCase):
    def test_builds_practical_plan_and_accounts_for_all_route_fuel(self):
        candidates = [
            _candidate(20, "3.50"),
            _candidate(450, "3.20"),
            _candidate(800, "3.00"),
            _candidate(1050, "3.40"),
        ]

        plan = optimize_fuel_purchases(candidates, 1200)

        self.assertEqual(plan.initial_fuel.route_station.route_mile, 20)
        total_gallons = plan.initial_fuel.gallons + sum(
            purchase.gallons for purchase in plan.purchases
        )
        self.assertAlmostEqual(total_gallons, 120)

    def test_carries_cheaper_fuel_through_expensive_station(self):
        plan = optimize_fuel_purchases(
            [
                _candidate(10, "2.00"),
                _candidate(300, "5.00"),
            ],
            500,
        )

        purchases = {
            purchase.route_station.route_mile: purchase
            for purchase in plan.purchases
        }
        self.assertNotIn(300, purchases)
        self.assertAlmostEqual(plan.initial_fuel.gallons, 50)
        self.assertEqual(purchases, {})

    def test_buys_only_enough_to_reach_first_cheaper_station(self):
        plan = optimize_fuel_purchases(
            [
                _candidate(10, "4.00"),
                _candidate(200, "3.00"),
                _candidate(450, "2.50"),
            ],
            700,
        )

        self.assertAlmostEqual(plan.initial_fuel.gallons, 20)
        self.assertNotIn(
            10,
            [
                purchase.route_station.route_mile
                for purchase in plan.purchases
            ],
        )

    def test_skips_intermediate_equal_price_stations(self):
        plan = optimize_fuel_purchases(
            [
                _candidate(10, "3.00"),
                _candidate(100, "3.00"),
                _candidate(200, "3.00"),
                _candidate(300, "3.00"),
            ],
            400,
        )

        self.assertEqual(plan.purchases, ())
        self.assertAlmostEqual(plan.initial_fuel.gallons, 40)

    def test_every_planned_leg_respects_maximum_range(self):
        plan = optimize_fuel_purchases(
            [_candidate(mile, "3.00") for mile in (20, 250, 600, 950, 1300)],
            1500,
        )
        selected_miles = [
            0,
            *[
                purchase.route_station.route_mile
                for purchase in plan.purchases
            ],
        ]
        legs = [
            *[
                right - left
                for left, right in zip(selected_miles, selected_miles[1:])
            ],
            1500 - selected_miles[-1],
        ]
        self.assertTrue(all(leg <= MAX_RANGE_MILES for leg in legs))

    def test_raises_when_station_gap_exceeds_range(self):
        with self.assertRaises(FuelPlanNotFoundError):
            optimize_fuel_purchases(
                [_candidate(20, "3.00"), _candidate(700, "2.90")],
                1300,
            )


def _candidate(route_mile, price):
    station = Station(
        opis_id=str(route_mile),
        name=f"Station {route_mile}",
        address="Interstate",
        city="Test City",
        state="NE",
        retail_price=Decimal(price),
        coordinate=Coordinate(40, -100),
    )
    return RouteStation(
        station=station,
        route_mile=route_mile,
        distance_to_route_miles=1,
    )
