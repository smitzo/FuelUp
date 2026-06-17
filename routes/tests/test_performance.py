import time
from decimal import Decimal

from django.test import SimpleTestCase

from routes.domain.entities import Coordinate, RouteStation, Station
from routes.domain.optimizer import optimize_fuel_purchases


class OptimizerPerformanceTests(SimpleTestCase):
    def test_thousand_station_route_completes_under_half_second(self):
        candidates = [
            RouteStation(
                station=Station(
                    opis_id=str(index),
                    name=f"Station {index}",
                    address="Interstate",
                    city=f"City {index}",
                    state="KS",
                    retail_price=Decimal("2.50")
                    + Decimal(index % 20) / Decimal("100"),
                    coordinate=Coordinate(40, -100),
                ),
                route_mile=index * 5,
                distance_to_route_miles=1,
            )
            for index in range(1, 1001)
        ]

        started = time.perf_counter()
        plan = optimize_fuel_purchases(candidates, 5_005)
        elapsed = time.perf_counter() - started

        self.assertTrue(plan.purchases)
        self.assertLess(elapsed, 0.5)
