import json
from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from routes.application.station_directory import (
    get_station_detail,
    search_station_directory,
)
from routes.domain.exceptions import StationNotFoundError
from routes.domain.fuel_data import (
    FuelType,
    GeographicPrecision,
    ObservationState,
    SourceType,
)
from routes.domain.market import MarketConfig
from routes.models import (
    FuelStation,
    PriceModerationEvent,
    PriceObservation,
    SourceRegistry,
    StationFuel,
    StationSnapshot,
)


class StationDirectoryTests(TestCase):
    def setUp(self):
        now = timezone.now()
        self.market = MarketConfig(
            code="GB",
            country_code="gb",
            country_name="Test Market",
            country_geography_id="test-market",
            currency_code="GBP",
            distance_unit="km",
            volume_unit="litre",
            efficiency_unit="km/litre",
            distance_units_per_mile=Decimal("1.609344"),
            time_value_per_hour=Decimal("10"),
            stop_penalty=Decimal("5"),
            route_cache_seconds=3600,
            station_source_slug="station-source",
            geocoding_source_slug="geocoder",
            routing_source_slug="router",
        )
        self.source = SourceRegistry.objects.create(
            slug="station-source",
            owner="Test publisher",
            purpose="station_catalogue",
            terms_url="https://example.com/terms",
            permitted_use="Test directory",
            attribution="Test catalogue attribution",
        )
        snapshot = StationSnapshot.objects.create(
            source=self.source,
            market_code="GB",
            version="directory-v1",
            source_generated_at=now,
            checksum_sha256="2" * 64,
            is_active=True,
            is_valid=True,
        )
        self.station = self._station(snapshot, "station-a", "Alpha Fuel", "City A")
        second = self._station(snapshot, "station-b", "Beta Fuel", "City B")
        for station in (self.station, second):
            StationFuel.objects.create(station=station, fuel_type=FuelType.PETROL)
        self.observation = PriceObservation.objects.create(
            market_code="GB",
            station=self.station,
            geography_precision=GeographicPrecision.STATION,
            geography_id=self.station.stable_id,
            fuel_type=FuelType.PETROL,
            unit_price=Decimal("100.125"),
            source=self.source,
            source_type=SourceType.COMMUNITY_REPORT,
            observed_at=now,
            effective_at=now,
            expires_at=now + timedelta(hours=24),
            state=ObservationState.ACCEPTED,
            contributor_id="private-contributor-id",
            evidence={"private_note": "must never appear"},
        )
        PriceModerationEvent.objects.create(
            observation=self.observation,
            actor_id="private-moderator-id",
            action="accept",
            reason_code="verified",
            previous_state=ObservationState.PENDING,
            new_state=ObservationState.ACCEPTED,
        )

    def _station(self, snapshot, stable_id, name, city):
        return FuelStation.objects.create(
            snapshot=snapshot,
            stable_id=stable_id,
            source_id=f"source-{stable_id}",
            name=name,
            city=city,
            latitude=Decimal("51.507400"),
            longitude=Decimal("-0.127800"),
            last_seen_at=timezone.now(),
        )

    def test_search_is_paginated_and_resolves_current_prices(self):
        result = search_station_directory(
            self.market,
            query="fuel",
            fuel_type=FuelType.PETROL,
            page=1,
            page_size=1,
        )

        self.assertEqual(result["pagination"]["total_items"], 2)
        self.assertEqual(result["pagination"]["total_pages"], 2)
        self.assertTrue(result["pagination"]["has_next"])
        price = result["stations"][0]["fuels"][0]["price"]
        self.assertEqual(price["unit_price"], "100.125")
        self.assertEqual(price["label"], "reported")
        self.assertEqual(price["sources"][0]["slug"], self.source.slug)

    def test_detail_does_not_leak_reporting_or_moderation_fields(self):
        result = get_station_detail(self.market, self.station.stable_id)
        encoded = json.dumps(result)

        self.assertNotIn("private-contributor-id", encoded)
        self.assertNotIn("private-moderator-id", encoded)
        self.assertNotIn("must never appear", encoded)
        self.assertNotIn("evidence", encoded)
        self.assertNotIn("moderation", encoded)

    def test_unknown_station_raises_typed_error(self):
        with self.assertRaises(StationNotFoundError):
            get_station_detail(self.market, "missing-station")
