from decimal import Decimal
from unittest.mock import patch

from django.test import SimpleTestCase

from routes.application.planner import METERS_PER_MILE, build_route_plan
from routes.domain.entities import Coordinate, GeocodedLocation, Station


class FakeMapClient:
    def geocode(self, query):
        longitude = -100 if query == "Start" else -99
        return GeocodedLocation(
            query=query,
            display_name=f"{query}, United States",
            coordinate=Coordinate(40, longitude),
        )

    def route(self, start, finish):
        return {
            "distance": 100 * METERS_PER_MILE,
            "duration": 7200,
            "geometry": {
                "type": "LineString",
                "coordinates": [[-100, 40], [-99.5, 40], [-99, 40]],
            },
        }


class RoutePlanServiceTests(SimpleTestCase):
    def test_builds_geojson_and_fuel_totals(self):
        station = Station(
            opis_id="10",
            name="Test Fuel",
            address="I-70",
            city="Test City",
            state="KS",
            retail_price=Decimal("3.00"),
            coordinate=Coordinate(40, -99.5),
        )

        with patch(
            "routes.application.planner.load_stations", return_value=(station,)
        ):
            result = build_route_plan("Start", "Finish", client=FakeMapClient())

        self.assertEqual(result["route"]["distance_miles"], 100)
        self.assertEqual(result["fuel_plan"]["total_gallons"], 10)
        self.assertEqual(result["fuel_plan"]["total_cost_usd"], 30)
        self.assertEqual(
            [feature["properties"]["kind"] for feature in result["route"]["geojson"]["features"]],
            ["route", "fuel_stop"],
        )
