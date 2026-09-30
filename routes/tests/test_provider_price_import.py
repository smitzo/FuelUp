from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from routes.application.price_import import import_provider_prices
from routes.domain.exceptions import ExternalServiceError
from routes.domain.fuel_data import FuelType, GeographicPrecision
from routes.infrastructure.mitra_prices import ReferencePrice
from routes.models import ObservationWatermark, PriceObservation, SourceRegistry


class ProviderPriceImportTests(TestCase):
    def setUp(self):
        self.source = SourceRegistry.objects.create(
            slug="api-mitra-fuel",
            purpose="third_party_price_reference",
            enabled=True,
            automated_access_allowed=True,
            permission_status="approved_for_pilot",
            permission_evidence="Test review",
            terms_url="https://example.com/terms",
            permitted_use="Test imports",
        )
        now = timezone.now()
        self.price = ReferencePrice(
            "in/gujarat",
            GeographicPrecision.STATE,
            FuelType.PETROL,
            Decimal("95.07"),
            now,
            now,
            now + timedelta(hours=24),
        )

    def test_import_replay_is_idempotent_and_keeps_provenance(self):
        batch, created = import_provider_prices(self.source.slug, [self.price])
        self.assertTrue(created)
        repeated, created = import_provider_prices(self.source.slug, [self.price])
        self.assertFalse(created)
        self.assertEqual(batch.pk, repeated.pk)
        self.assertEqual(PriceObservation.objects.count(), 1)
        self.assertEqual(
            PriceObservation.objects.get().source_type, "third_party_reference"
        )
        self.assertEqual(ObservationWatermark.objects.get(scope="IN").version, 1)

    def test_disabled_or_unreviewed_source_cannot_import(self):
        self.source.enabled = False
        self.source.save()
        with self.assertRaises(ExternalServiceError):
            import_provider_prices(self.source.slug, [self.price])
        self.assertFalse(PriceObservation.objects.exists())
