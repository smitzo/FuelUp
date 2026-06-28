from datetime import timedelta
from decimal import Decimal

from django.test import SimpleTestCase
from django.utils import timezone

from routes.domain.fuel_data import (
    Confidence,
    FuelType,
    GeographicPrecision,
    ObservationState,
    PriceLabel,
    PriceObservationValue,
    ResolvedPriceQuote,
    SourceType,
    VehicleProfile,
)


class VehicleProfileTests(SimpleTestCase):
    def test_computes_usable_capacity_and_range(self):
        profile = VehicleProfile(
            fuel_type=FuelType.PETROL,
            tank_capacity=Decimal("35"),
            efficiency=Decimal("18"),
            starting_fuel=Decimal("8"),
            reserve_fuel=Decimal("3"),
            fuel_grade=" Regular ",
        )

        self.assertEqual(profile.usable_capacity, Decimal("32"))
        self.assertEqual(profile.maximum_range, Decimal("576"))
        self.assertEqual(profile.fuel_grade, "regular")

    def test_rejects_starting_fuel_plus_reserve_above_capacity(self):
        with self.assertRaisesRegex(ValueError, "cannot exceed"):
            VehicleProfile(
                fuel_type=FuelType.DIESEL,
                tank_capacity=Decimal("40"),
                efficiency=Decimal("15"),
                starting_fuel=Decimal("38"),
                reserve_fuel=Decimal("3"),
            )

    def test_rejects_non_positive_capacity_and_efficiency(self):
        with self.assertRaisesRegex(ValueError, "greater than zero"):
            VehicleProfile(
                fuel_type=FuelType.PETROL,
                tank_capacity=Decimal("0"),
                efficiency=Decimal("18"),
                starting_fuel=Decimal("0"),
                reserve_fuel=Decimal("0"),
            )


class PriceObservationValueTests(SimpleTestCase):
    def test_current_observation_requires_accepted_and_unexpired(self):
        now = timezone.now()
        observation = PriceObservationValue(
            observation_id="obs-1",
            station_id="osm-node-1",
            geography_precision=GeographicPrecision.STATION,
            geography_id="osm-node-1",
            fuel_type=FuelType.PETROL,
            fuel_grade=None,
            unit_price=Decimal("101.250"),
            source_type=SourceType.COMMUNITY_REPORT,
            source_id="fuelup-community",
            observed_at=now,
            effective_at=now,
            received_at=now,
            expires_at=now + timedelta(hours=24),
            state=ObservationState.ACCEPTED,
        )

        self.assertTrue(observation.is_current(now + timedelta(hours=1)))
        self.assertFalse(observation.is_current(now + timedelta(hours=24)))

    def test_rejects_naive_timestamps(self):
        now = timezone.now().replace(tzinfo=None)
        with self.assertRaisesRegex(ValueError, "timezone-aware"):
            PriceObservationValue(
                observation_id="obs-1",
                station_id=None,
                geography_precision=GeographicPrecision.CITY,
                geography_id="ahmedabad",
                fuel_type=FuelType.DIESEL,
                fuel_grade=None,
                unit_price=Decimal("92.000"),
                source_type=SourceType.OFFICIAL_REFERENCE,
                source_id="ppac-price-reference",
                observed_at=now,
                effective_at=now,
                received_at=now,
                expires_at=now + timedelta(hours=36),
            )

    def test_unavailable_quote_has_no_numeric_price(self):
        quote = ResolvedPriceQuote.unavailable()

        self.assertIsNone(quote.unit_price)
        self.assertEqual(quote.label, PriceLabel.UNAVAILABLE)
        self.assertEqual(quote.confidence, Confidence.UNAVAILABLE)
