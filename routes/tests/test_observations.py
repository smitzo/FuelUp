from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from routes.application.observations import (
    ObservationCreate,
    transition_observation,
    validate_and_store_observation,
)
from routes.domain.fuel_data import (
    FuelType,
    GeographicPrecision,
    ObservationState,
    SourceType,
)
from routes.models import (
    FuelStation,
    ObservationWatermark,
    PriceModerationEvent,
    SourceRegistry,
    StationFuel,
    StationSnapshot,
)


class ObservationServiceTests(TestCase):
    def setUp(self):
        now = timezone.now()
        self.source = SourceRegistry.objects.create(
            slug="community-test",
            owner="Test publisher",
            purpose="community_prices",
            terms_url="https://example.com/terms",
            permitted_use="Test observations",
            automated_access_allowed=True,
            enabled=True,
        )
        snapshot = StationSnapshot.objects.create(
            source=self.source,
            market_code="GB",
            version="gb-test-v1",
            source_generated_at=now,
            checksum_sha256="1" * 64,
            is_active=True,
            is_valid=True,
        )
        self.station = FuelStation.objects.create(
            snapshot=snapshot,
            stable_id="station-1",
            source_id="source-station-1",
            name="Market Neutral Fuel",
            latitude=Decimal("51.507400"),
            longitude=Decimal("-0.127800"),
            last_seen_at=now,
        )
        StationFuel.objects.create(
            station=self.station,
            fuel_type=FuelType.PETROL,
        )

    def command(self, **overrides):
        now = timezone.now()
        values = {
            "market_code": "GB",
            "source": self.source,
            "source_type": SourceType.COMMUNITY_REPORT,
            "station": self.station,
            "geography_precision": GeographicPrecision.STATION,
            "geography_id": self.station.stable_id,
            "fuel_type": FuelType.PETROL,
            "fuel_grade": "",
            "unit_price": Decimal("100"),
            "observed_at": now,
            "effective_at": now,
            "expires_at": now + timedelta(hours=24),
            "contributor_id": "contributor-a",
        }
        values.update(overrides)
        return ObservationCreate(**values)

    def test_accepted_observation_advances_market_watermark(self):
        stored = validate_and_store_observation(self.command())

        self.assertEqual(stored.outcome.state, ObservationState.ACCEPTED)
        self.assertEqual(
            ObservationWatermark.objects.get(scope="GB").version,
            1,
        )

    def test_duplicate_is_audited_without_advancing_watermark(self):
        validate_and_store_observation(self.command())
        stored = validate_and_store_observation(self.command())

        self.assertEqual(stored.outcome.state, ObservationState.REJECTED)
        self.assertEqual(stored.outcome.reason, "duplicate")
        self.assertEqual(
            ObservationWatermark.objects.get(scope="GB").version,
            1,
        )

    def test_outlier_is_quarantined(self):
        validate_and_store_observation(self.command(contributor_id="source-a"))
        validate_and_store_observation(
            self.command(unit_price=Decimal("101"), contributor_id="source-b")
        )
        stored = validate_and_store_observation(
            self.command(unit_price=Decimal("150"), contributor_id="source-c")
        )

        self.assertEqual(stored.outcome.state, ObservationState.QUARANTINED)
        self.assertEqual(stored.outcome.reason, "price_outlier")

    def test_incompatible_fuel_is_rejected(self):
        stored = validate_and_store_observation(self.command(fuel_type=FuelType.DIESEL))

        self.assertEqual(stored.outcome.reason, "incompatible_fuel")
        self.assertFalse(ObservationWatermark.objects.exists())

    def test_moderation_is_audited_and_invalidates_cached_prices(self):
        stored = validate_and_store_observation(self.command())

        transition_observation(
            stored.observation.id,
            new_state=ObservationState.RETRACTED,
            actor_id="moderator-1",
            reason_code="publisher_correction",
        )

        stored.observation.refresh_from_db()
        event = PriceModerationEvent.objects.get(observation=stored.observation)
        self.assertEqual(stored.observation.state, ObservationState.RETRACTED)
        self.assertEqual(event.previous_state, ObservationState.ACCEPTED)
        self.assertEqual(event.new_state, ObservationState.RETRACTED)
        self.assertEqual(
            ObservationWatermark.objects.get(scope="GB").version,
            2,
        )
