from unittest.mock import patch

from django.core.cache import cache
from django.test import SimpleTestCase, override_settings

from routes.domain.entities import Coordinate, GeocodedLocation
from routes.domain.exceptions import LocationNotFoundError, RouteNotFoundError
from routes.infrastructure.map_client import MapClient


@override_settings(
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
)
class MapClientTests(SimpleTestCase):
    def setUp(self):
        cache.clear()
        self.client = MapClient()

    def test_geocode_limits_result_to_the_united_states_and_caches_it(self):
        response = [
            {
                "display_name": "Austin, Travis County, Texas, United States",
                "lat": "30.2672",
                "lon": "-97.7431",
                "address": {"country_code": "us"},
            }
        ]

        with patch.object(
            self.client, "_nominatim_request", return_value=response
        ) as request:
            first = self.client.geocode("Austin, TX")
            second = self.client.geocode("Austin, TX")

        self.assertEqual(first, second)
        self.assertEqual(first.coordinate.latitude, 30.2672)
        request.assert_called_once()
        self.assertIn("countrycodes=us", request.call_args.args[0])

    def test_geocode_rejects_non_us_result(self):
        response = [
            {
                "display_name": "Toronto, Ontario, Canada",
                "lat": "43.65",
                "lon": "-79.38",
                "address": {"country_code": "ca"},
            }
        ]

        with patch.object(self.client, "_nominatim_request", return_value=response):
            with self.assertRaises(LocationNotFoundError):
                self.client.geocode("Toronto")

    def test_routes_returns_osrm_alternatives(self):
        start = GeocodedLocation("A", "A", Coordinate(30, -97))
        finish = GeocodedLocation("B", "B", Coordinate(31, -96))
        route = {
            "distance": 1000,
            "duration": 100,
            "geometry": {"type": "LineString", "coordinates": [[-97, 30], [-96, 31]]},
        }

        with patch.object(
            self.client, "_request", return_value={"code": "Ok", "routes": [route]}
        ):
            self.assertEqual(self.client.routes(start, finish), [route])

    def test_routes_raises_when_osrm_has_no_route(self):
        start = GeocodedLocation("A", "A", Coordinate(30, -97))
        finish = GeocodedLocation("B", "B", Coordinate(31, -96))

        with patch.object(
            self.client, "_request", return_value={"code": "NoRoute", "routes": []}
        ):
            with self.assertRaises(RouteNotFoundError):
                self.client.routes(start, finish)
