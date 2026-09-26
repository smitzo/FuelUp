from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from routes.domain.exceptions import ExternalServiceError
from routes.infrastructure.heigit_client import HeiGitRoutingClient


@override_settings(HEIGIT_API_KEY="test-only-key", ROUTE_ALTERNATIVES=3)
class HeiGitClientTests(SimpleTestCase):
    def setUp(self):
        self.locations = [
            SimpleNamespace(
                coordinate=SimpleNamespace(longitude=72.5 + offset, latitude=23)
            )
            for offset in (0, 1)
        ]
        self.response = {
            "features": [
                {
                    "properties": {
                        "summary": {"distance": "1000.5", "duration": "100"}
                    },
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [["72.5", "23"], ["73.5", "23"]],
                    },
                }
            ]
        }

    @patch("routes.infrastructure.heigit_client.request_json")
    def test_lon_lat_order_auth_and_geojson_normalization(self, request):
        request.return_value = self.response
        routes = HeiGitRoutingClient().routes_through(self.locations)
        self.assertEqual(routes[0]["distance"], 1000.5)
        self.assertEqual(routes[0]["geometry"]["coordinates"][0], [72.5, 23])
        self.assertEqual(
            request.call_args.kwargs["payload"]["coordinates"][0], [72.5, 23]
        )
        self.assertIn("alternative_routes", request.call_args.kwargs["payload"])
        HeiGitRoutingClient().routes_through([*self.locations, self.locations[0]])
        self.assertNotIn("alternative_routes", request.call_args.kwargs["payload"])

    @patch("routes.infrastructure.heigit_client.request_json")
    def test_malformed_provider_geometry_is_typed(self, request):
        self.response["features"][0]["geometry"]["coordinates"][0][0] = "nan"
        request.return_value = self.response
        with self.assertRaises(ExternalServiceError):
            HeiGitRoutingClient().routes_through(self.locations)

    @override_settings(HEIGIT_API_KEY="")
    def test_missing_key_does_not_make_request(self):
        with self.assertRaises(ExternalServiceError):
            HeiGitRoutingClient().routes_through(self.locations)
