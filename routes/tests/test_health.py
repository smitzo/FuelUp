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

    @patch("routes.api.views._market_data_ready", return_value=True)
    def test_readiness_checks_cache_and_market_data(self, market_data):
        cache.clear()

        response = self.client.get(reverse("health-ready"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["checks"],
            {"station_prices": True, "cache": True},
        )

    @patch("routes.api.views._market_data_ready", return_value=False)
    def test_readiness_fails_when_market_data_is_unavailable(self, market_data):
        response = self.client.get(reverse("health-ready"))

        self.assertEqual(response.status_code, 503)
        self.assertFalse(response.json()["checks"]["station_prices"])
