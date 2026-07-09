from datetime import timedelta
from decimal import Decimal

from django.test import SimpleTestCase
from django.utils import timezone

from routes.domain.entities import Coordinate, PricedStation, Station
from routes.domain.fuel_data import (
    Confidence,
    FuelType,
    GeographicPrecision,
    PriceLabel,
    ResolvedPriceQuote,
)
from routes.domain.geometry import route_priced_stations, route_stations


class RouteGeometryTests(SimpleTestCase):
    def test_matches_nearby_station_and_excludes_distant_station(self):
        nearby = _station("1", 40.02, -99.5, "3.10")
        distant = _station("2", 42.0, -99.5, "2.50")
        route = [[-100.0, 40.0], [-99.5, 40.0], [-99.0, 40.0]]

        matches = route_stations([nearby, distant], route, 52.0)

        self.assertEqual([match.station.opis_id for match in matches], ["1"])
        self.assertAlmostEqual(matches[0].route_mile, 26.0, delta=1)

    def test_projects_station_onto_segment_not_only_route_vertices(self):
        station = _station("1", 40.1, -99.5, "3.10")

        matches = route_stations(
            [station],
            [[-100.0, 40.0], [-99.0, 40.0]],
            52.0,
        )

        self.assertEqual(len(matches), 1)
        self.assertAlmostEqual(matches[0].route_mile, 26.0, delta=0.5)
        self.assertAlmostEqual(matches[0].distance_to_route_miles, 6.9, delta=0.3)

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

    def test_matches_priced_station_in_configured_distance_units(self):
        station = _priced_station("osm-node-1", 23.05, 72.6, "101.20")

        matches = route_priced_stations(
            [station],
            [[72.5, 23.0], [72.7, 23.0]],
            route_distance=20,
            maximum_detour=10,
            distance_units_per_mile=Decimal("1.609344"),
        )

        self.assertEqual(
            [match.station.stable_id for match in matches],
            ["osm-node-1"],
        )
        self.assertAlmostEqual(matches[0].route_distance, 10, delta=1)
        self.assertLess(matches[0].distance_to_route, 6)


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


def _priced_station(stable_id, latitude, longitude, price):
    now = timezone.now()
    return PricedStation(
        stable_id=stable_id,
        name=f"Station {stable_id}",
        address="Test Road",
        city="Ahmedabad",
        state="Gujarat",
        coordinate=Coordinate(latitude, longitude),
        fuel_types=frozenset({FuelType.PETROL}),
        price_quote=ResolvedPriceQuote(
            unit_price=Decimal(price),
            label=PriceLabel.REFERENCE,
            geography_precision=GeographicPrecision.CITY,
            confidence=Confidence.LOW,
            as_of=now,
            expires_at=now + timedelta(hours=36),
        ),
    )
