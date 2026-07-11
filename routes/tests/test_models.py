from datetime import timedelta
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from routes.api.views import _market_data_ready
from routes.domain.fuel_data import (
    FuelType,
    GeographicPrecision,
    ObservationState,
    SourceType,
)
from routes.models import (
    FuelStation,
    PriceObservation,
    SourceRegistry,
    StationFuel,
    StationSnapshot,
)


class FuelDataModelTests(TestCase):
    def setUp(self):
        self.source = SourceRegistry.objects.create(
            slug="geofabrik-india-osm",
            owner="OpenStreetMap contributors",
            purpose="station_catalogue",
            terms_url="https://download.geofabrik.de/asia/india.html",
            permission_evidence="ODbL",
            permitted_use="Derived station catalogue",
            attribution="OpenStreetMap contributors",
            automated_access_allowed=True,
            enabled=True,
            refresh_budget_per_day=1,
        )
        self.snapshot = StationSnapshot.objects.create(
            source=self.source,
            market_code="IN",
            version="india-2026-08-10",
            source_generated_at=timezone.now(),
            checksum_sha256="a" * 64,
            is_active=True,
            is_valid=True,
            quality_metrics={"station_count": 1},
        )
        self.station = FuelStation.objects.create(
            snapshot=self.snapshot,
            stable_id="osm-node-1",
            source_id="node/1",
            name="India Test Fuel",
            city="Ahmedabad",
            state="Gujarat",
            latitude=Decimal("23.022500"),
            longitude=Decimal("72.571400"),
            last_seen_at=timezone.now(),
        )

    def test_source_fetch_requires_permission_and_enablement(self):
        self.assertTrue(self.source.can_fetch)
        self.source.enabled = False
        self.assertFalse(self.source.can_fetch)

    def test_only_one_station_snapshot_can_be_active(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            StationSnapshot.objects.create(
                source=self.source,
                market_code="IN",
                version="india-2026-08-11",
                source_generated_at=timezone.now(),
                checksum_sha256="b" * 64,
                is_active=True,
                is_valid=True,
            )

    def test_station_fuel_is_unique_by_type_and_grade(self):
        StationFuel.objects.create(
            station=self.station,
            fuel_type=FuelType.PETROL,
            grade="regular",
        )

        with self.assertRaises(IntegrityError), transaction.atomic():
            StationFuel.objects.create(
                station=self.station,
                fuel_type=FuelType.PETROL,
                grade="regular",
            )

    def test_observation_requires_positive_price_and_later_expiry(self):
        now = timezone.now()
        observation = PriceObservation.objects.create(
            market_code="IN",
            station=self.station,
            geography_precision=GeographicPrecision.STATION,
            geography_id=self.station.stable_id,
            fuel_type=FuelType.PETROL,
            unit_price=Decimal("101.250"),
            source=self.source,
            source_type=SourceType.COMMUNITY_REPORT,
            observed_at=now,
            effective_at=now,
            expires_at=now + timedelta(hours=24),
            state=ObservationState.ACCEPTED,
        )

        self.assertEqual(observation.unit_price, Decimal("101.250"))

        with self.assertRaises(IntegrityError), transaction.atomic():
            PriceObservation.objects.create(
                market_code="IN",
                geography_precision=GeographicPrecision.CITY,
                geography_id="ahmedabad",
                fuel_type=FuelType.PETROL,
                unit_price=Decimal("100"),
                source=self.source,
                source_type=SourceType.OFFICIAL_REFERENCE,
                observed_at=now,
                effective_at=now,
                expires_at=now - timedelta(minutes=1),
                state=ObservationState.ACCEPTED,
            )


class MarketDataReadinessTests(TestCase):
    def setUp(self):
        now = timezone.now()
        self.source = SourceRegistry.objects.create(
            slug="india-readiness-source",
            owner="Test",
            purpose="station_catalogue",
            terms_url="https://example.com/terms",
            permitted_use="Tests",
        )
        snapshot = StationSnapshot.objects.create(
            source=self.source,
            market_code="IN",
            version="india-readiness-v1",
            source_generated_at=now,
            checksum_sha256="c" * 64,
            is_active=True,
            is_valid=True,
        )
        self.station = FuelStation.objects.create(
            snapshot=snapshot,
            stable_id="osm-node-ready",
            source_id="node/ready",
            name="Readiness Fuel",
            latitude=Decimal("23.022500"),
            longitude=Decimal("72.571400"),
            last_seen_at=now,
        )
        StationFuel.objects.create(
            station=self.station,
            fuel_type=FuelType.PETROL,
        )

    def test_requires_current_accepted_compatible_price(self):
        self.assertFalse(_market_data_ready())
        now = timezone.now()
        PriceObservation.objects.create(
            market_code="IN",
            station=self.station,
            geography_precision=GeographicPrecision.STATION,
            geography_id=self.station.stable_id,
            fuel_type=FuelType.PETROL,
            unit_price=Decimal("101.250"),
            source=self.source,
            source_type=SourceType.COMMUNITY_REPORT,
            observed_at=now,
            effective_at=now,
            expires_at=now + timedelta(hours=24),
            state=ObservationState.ACCEPTED,
        )

        self.assertTrue(_market_data_ready())
