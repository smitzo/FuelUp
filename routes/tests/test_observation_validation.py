from datetime import UTC, datetime, timedelta
from decimal import Decimal

from django.test import SimpleTestCase

from routes.domain.fuel_data import ObservationState
from routes.domain.observation_validation import (
    ObservationPolicy,
    ObservationSubmission,
    ValidationContext,
    validate_observation,
)


class ObservationValidationTests(SimpleTestCase):
    def setUp(self):
        self.now = datetime(2026, 8, 10, 12, tzinfo=UTC)
        self.policy = ObservationPolicy(
            min_unit_price=Decimal("20"),
            max_unit_price=Decimal("300"),
            max_age=timedelta(days=2),
            future_skew=timedelta(minutes=5),
            duplicate_window=timedelta(minutes=30),
            rapid_update_window=timedelta(minutes=10),
            absolute_outlier_tolerance=Decimal("5"),
            relative_outlier_tolerance=Decimal("0.10"),
        )

    def validate(self, price="100", observed_at=None, **context):
        return validate_observation(
            ObservationSubmission(
                unit_price=Decimal(price),
                observed_at=observed_at or self.now,
                received_at=self.now,
            ),
            ValidationContext(**context),
            self.policy,
        )

    def test_accepts_plausible_observation(self):
        outcome = self.validate(comparable_prices=(Decimal("98"), Decimal("102")))

        self.assertEqual(outcome.state, ObservationState.ACCEPTED)
        self.assertEqual(outcome.reason, "accepted")

    def test_rejects_non_finite_or_out_of_bounds_prices(self):
        for price in ("NaN", "Infinity", "19.999", "300.001"):
            with self.subTest(price=price):
                self.assertEqual(
                    self.validate(price=price).state,
                    ObservationState.REJECTED,
                )

    def test_rejects_invalid_time_and_station_relationships(self):
        cases = (
            ({"observed_at": self.now + timedelta(minutes=6)}, "observed_in_future"),
            ({"observed_at": self.now - timedelta(days=3)}, "observation_too_old"),
            ({"compatible_fuel": False}, "incompatible_fuel"),
            (
                {"station_accepting_reports": False},
                "station_not_accepting_reports",
            ),
            ({"duplicate": True}, "duplicate"),
        )
        for values, reason in cases:
            with self.subTest(reason=reason):
                self.assertEqual(self.validate(**values).reason, reason)

    def test_quarantines_rapid_updates_and_statistical_outliers(self):
        rapid = self.validate(rapid_update=True)
        outlier = self.validate(
            price="130",
            comparable_prices=(Decimal("99"), Decimal("100"), Decimal("101")),
        )

        self.assertEqual(rapid.state, ObservationState.QUARANTINED)
        self.assertEqual(rapid.reason, "rapid_update")
        self.assertEqual(outlier.state, ObservationState.QUARANTINED)
        self.assertEqual(outlier.reason, "price_outlier")

    def test_policy_rejects_invalid_configuration(self):
        with self.assertRaises(ValueError):
            ObservationPolicy(
                min_unit_price=Decimal("300"),
                max_unit_price=Decimal("20"),
                max_age=timedelta(days=2),
                future_skew=timedelta(minutes=5),
                duplicate_window=timedelta(minutes=30),
                rapid_update_window=timedelta(minutes=10),
                absolute_outlier_tolerance=Decimal("5"),
                relative_outlier_tolerance=Decimal("0.10"),
            )
