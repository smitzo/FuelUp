from unittest.mock import patch

from django.core.cache import cache
from django.test import SimpleTestCase
from django.urls import reverse


class HealthEndpointTests(SimpleTestCase):
    def test_liveness_returns_release_metadata(self):
        response = self.client.get(reverse("health-live"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["service"], "fuelup-api")
        self.assertIn("release", response.json())

    @patch(
        "routes.api.views.load_stations",
        return_value=("station",),
    )
    def test_readiness_checks_cache_and_station_data(self, stations):
        cache.clear()

        response = self.client.get(reverse("health-ready"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["checks"],
            {"station_data": True, "cache": True},
        )

    @patch("routes.api.views.load_stations", side_effect=OSError("missing"))
    def test_readiness_fails_when_station_data_is_unavailable(self, stations):
        response = self.client.get(reverse("health-ready"))

        self.assertEqual(response.status_code, 503)
        self.assertFalse(response.json()["checks"]["station_data"])
