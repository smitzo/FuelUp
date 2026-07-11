import time
from unittest.mock import patch

from django.core.cache import cache
from django.test import SimpleTestCase, override_settings

from routes.domain.entities import Coordinate, GeocodedLocation
from routes.domain.exceptions import (
    LocationNotFoundError,
    RouteNotFoundError,
    UnsupportedCountryError,
)
from routes.infrastructure.map_client import (
    MapClient,
    MarketMapClient,
    _wait_for_nominatim_slot,
)
from routes.tests.factories import market_config


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

    @patch("routes.infrastructure.map_client._require_source_enabled")
    def test_market_geocode_uses_country_filter_and_typed_foreign_error(
        self, source_enabled
    ):
        client = MarketMapClient(market_config())
        india_response = [
            {
                "display_name": "Ahmedabad, Gujarat, India",
                "lat": "23.0225",
                "lon": "72.5714",
                "address": {"country_code": "in"},
            }
        ]
        with patch.object(
            client, "_nominatim_request", return_value=india_response
        ) as request:
            location = client.geocode("Ahmedabad")

        self.assertEqual(location.coordinate.latitude, 23.0225)
        self.assertIn("countrycodes=in", request.call_args.args[0])

        foreign_response = [
            {
                "display_name": "Lahore, Pakistan",
                "lat": "31.5204",
                "lon": "74.3587",
                "address": {"country_code": "pk"},
            }
        ]
        with patch.object(
            client, "_nominatim_request", return_value=foreign_response
        ):
            with self.assertRaises(UnsupportedCountryError):
                client.geocode("Lahore")

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
        ) as request:
            self.assertEqual(self.client.routes(start, finish), [route])

        self.assertIn("overview=simplified", request.call_args.args[1])

    def test_routes_raises_when_osrm_has_no_route(self):
        start = GeocodedLocation("A", "A", Coordinate(30, -97))
        finish = GeocodedLocation("B", "B", Coordinate(31, -96))

        with patch.object(
            self.client, "_request", return_value={"code": "NoRoute", "routes": []}
        ):
            with self.assertRaises(RouteNotFoundError):
                self.client.routes(start, finish)

    def test_routes_through_keeps_waypoint_order_in_one_request(self):
        locations = (
            GeocodedLocation("A", "A", Coordinate(23, 72)),
            GeocodedLocation("W", "W", Coordinate(22, 73)),
            GeocodedLocation("B", "B", Coordinate(21, 74)),
        )
        route = {
            "distance": 1000,
            "duration": 100,
            "geometry": {"type": "LineString", "coordinates": []},
        }
        with patch.object(
            self.client,
            "_request",
            return_value={"code": "Ok", "routes": [route]},
        ) as request:
            self.client.routes_through(locations)

        self.assertIn("72,23;73,22;74,21", request.call_args.args[1])

    @patch("routes.infrastructure.map_client.time.sleep")
    @patch(
        "routes.infrastructure.map_client.cache.get",
        return_value=None,
    )
    def test_nominatim_wait_uses_local_process_interval(
        self,
        cache_get,
        sleep,
    ):
        with patch(
            "routes.infrastructure.map_client._last_nominatim_request",
            time.monotonic(),
        ):
            _wait_for_nominatim_slot()

        sleep.assert_called_once()
