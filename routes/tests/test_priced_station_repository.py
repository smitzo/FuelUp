from datetime import timedelta
from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from routes.domain.fuel_data import (
    FuelType,
    GeographicPrecision,
    ObservationState,
    PriceLabel,
    SourceType,
)
from routes.infrastructure.priced_station_repository import (
    PricedStationRepository,
)
from routes.models import (
    FuelStation,
    ObservationWatermark,
    PriceObservation,
    SourceRegistry,
    StationFuel,
    StationSnapshot,
)
from routes.tests.factories import market_config


class PricedStationRepositoryTests(TestCase):
    def setUp(self):
        self.now = timezone.now()
        self.market = market_config()
        self.source = SourceRegistry.objects.create(
            slug="market-test-source",
            owner="Test",
            purpose="station_catalogue",
            terms_url="https://example.com/terms",
            permission_status="approved_test",
            permission_evidence="Test fixture",
            permitted_use="Tests",
            attribution="Test attribution",
            automated_access_allowed=True,
            enabled=True,
            refresh_budget_per_day=1,
        )
        snapshot = StationSnapshot.objects.create(
            source=self.source,
            market_code=self.market.code,
            version="test-v1",
            source_generated_at=self.now,
            checksum_sha256="a" * 64,
            is_active=True,
            is_valid=True,
        )
        self.station = FuelStation.objects.create(
            snapshot=snapshot,
            stable_id="osm-node-1",
            source_id="node/1",
            name="Ahmedabad Test Fuel",
            city="Ahmedabad",
            district="Ahmedabad",
            state="Gujarat",
            latitude=Decimal("23.022500"),
            longitude=Decimal("72.571400"),
            last_seen_at=self.now,
        )
        StationFuel.objects.create(
            station=self.station,
            fuel_type=FuelType.PETROL,
            grade="",
        )
        ObservationWatermark.objects.create(scope=self.market.code, version=7)

    def test_loads_active_catalogue_and_resolves_station_consensus(self):
        self._price("101.00", contributor="driver-a")
        self._price("102.00", contributor="driver-b")

        catalogue = PricedStationRepository(self.market).load(
            fuel_type=FuelType.PETROL,
            fuel_grade=None,
            at=self.now,
        )

        self.assertEqual(catalogue.snapshot_version, "test-v1")
        self.assertEqual(catalogue.observation_watermark, 7)
        self.assertEqual(len(catalogue.stations), 1)
        quote = catalogue.stations[0].price_quote
        self.assertEqual(quote.unit_price, Decimal("101.500"))
        self.assertEqual(quote.label, PriceLabel.REPORTED)

    def test_applies_city_reference_without_changing_precision(self):
        PriceObservation.objects.create(
            market_code=self.market.code,
            geography_precision=GeographicPrecision.CITY,
            geography_id=" Ahmedabad ",
            fuel_type=FuelType.PETROL,
            unit_price=Decimal("99.500"),
            source=self.source,
            source_type=SourceType.OFFICIAL_REFERENCE,
            observed_at=self.now - timedelta(hours=1),
            effective_at=self.now - timedelta(hours=1),
            expires_at=self.now + timedelta(hours=35),
            state=ObservationState.ACCEPTED,
        )

        station = PricedStationRepository(self.market).load(
            fuel_type=FuelType.PETROL,
            fuel_grade=None,
            at=self.now,
        ).stations[0]

        self.assertEqual(
            station.price_quote.geography_precision,
            GeographicPrecision.CITY,
        )
        self.assertEqual(station.price_quote.label, PriceLabel.REFERENCE)

    def test_inferred_fuel_is_not_used_for_recommendations(self):
        StationFuel.objects.filter(station=self.station).update(is_inferred=True)
        catalogue = PricedStationRepository(self.market).load(
            fuel_type=FuelType.PETROL, fuel_grade=None, at=self.now,
        )
        self.assertEqual(catalogue.stations, ())

    def test_excludes_station_that_does_not_offer_requested_fuel(self):
        catalogue = PricedStationRepository(self.market).load(
            fuel_type=FuelType.DIESEL,
            fuel_grade=None,
            at=self.now,
        )

        self.assertEqual(catalogue.stations, ())

    def _price(self, price, contributor):
        return PriceObservation.objects.create(
            market_code=self.market.code,
            station=self.station,
            geography_precision=GeographicPrecision.STATION,
            geography_id=self.station.stable_id,
            fuel_type=FuelType.PETROL,
            unit_price=Decimal(price),
            source=self.source,
            source_type=SourceType.COMMUNITY_REPORT,
            observed_at=self.now - timedelta(hours=1),
            effective_at=self.now - timedelta(hours=1),
            expires_at=self.now + timedelta(hours=23),
            state=ObservationState.ACCEPTED,
            contributor_id=contributor,
        )


class SyncSourceRegistryCommandTests(TestCase):
    def test_synchronizes_approved_and_disabled_sources(self):
        output = StringIO()

        call_command("sync_source_registry", stdout=output)

        self.assertIn("Synchronized 11 data sources", output.getvalue())
        self.assertTrue(
            SourceRegistry.objects.get(slug="geofabrik-india-osm").can_fetch
        )
        ppac = SourceRegistry.objects.get(slug="ppac-price-reference")
        self.assertFalse(ppac.can_fetch)
        self.assertEqual(ppac.permission_status, "unresolved")
