from django.test import TestCase
from django.utils import timezone

from routes.models import SourceRegistry, StationSnapshot


class DataStatusTests(TestCase):
    def test_empty_market_is_explicit_and_contains_no_secrets(self):
        response = self.client.get("/api/v2/data-status/")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["market"]["code"], "IN")
        self.assertFalse(payload["catalogue"]["available"])
        self.assertEqual(payload["current_price_scopes"], [])
        self.assertNotIn("key", response.content.decode().casefold())

    def test_active_catalogue_status_does_not_require_prices(self):
        source = SourceRegistry.objects.create(slug="osm")
        StationSnapshot.objects.create(
            source=source,
            market_code="IN",
            version="test",
            source_generated_at=timezone.now(),
            checksum_sha256="a" * 64,
            is_active=True,
            is_valid=True,
        )
        payload = self.client.get("/api/v2/data-status/").json()
        self.assertTrue(payload["catalogue"]["available"])
        self.assertEqual(payload["catalogue"]["stations"], 0)
