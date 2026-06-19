from decimal import Decimal

from django.test import SimpleTestCase

from routes.domain.entities import Coordinate, Station
from routes.domain.geometry import route_stations


class RouteGeometryTests(SimpleTestCase):
    def test_matches_nearby_station_and_excludes_distant_station(self):
        nearby = _station("1", 40.02, -99.5, "3.10")
        distant = _station("2", 42.0, -99.5, "2.50")
        route = [[-100.0, 40.0], [-99.5, 40.0], [-99.0, 40.0]]

        matches = route_stations([nearby, distant], route, 52.0)

        self.assertEqual([match.station.opis_id for match in matches], ["1"])
        self.assertAlmostEqual(matches[0].route_mile, 26.0, delta=1)

    def test_keeps_cheapest_duplicate_city_candidate(self):
        expensive = _station("1", 40.0, -99.5, "3.50")
        cheap = _station("2", 40.0, -99.5, "3.10")

        matches = route_stations(
            [expensive, cheap],
            [[-100.0, 40.0], [-99.5, 40.0], [-99.0, 40.0]],
            52.0,
        )

        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].station.opis_id, "2")


def _station(opis_id, latitude, longitude, price):
    return Station(
        opis_id=opis_id,
        name=f"Station {opis_id}",
        address="Interstate",
        city="Test City",
        state="KS",
        retail_price=Decimal(price),
        coordinate=Coordinate(latitude, longitude),
    )
