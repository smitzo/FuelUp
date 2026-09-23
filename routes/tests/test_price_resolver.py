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
    SourceType,
)
from routes.domain.price_resolver import resolve_price_quote


class PriceResolverTests(SimpleTestCase):
    def setUp(self):
        self.now = timezone.now()

    def test_independent_consensus_excludes_outlier(self):
        observations = [
            self._observation("one", "101.00", contributor="a"),
            self._observation("two", "102.00", contributor="b"),
            self._observation("outlier", "140.00", contributor="c"),
        ]

        quote = self._resolve(observations)

        self.assertEqual(quote.unit_price, Decimal("101.50"))
        self.assertEqual(quote.label, PriceLabel.REPORTED)
        self.assertEqual(quote.confidence, Confidence.MEDIUM)
        self.assertEqual(quote.observation_ids, ("one", "two"))

    def test_one_contributor_cannot_create_consensus(self):
        observations = [
            self._observation("old", "100.00", contributor="same", age_hours=2),
            self._observation("new", "101.00", contributor="same", age_hours=1),
        ]

        quote = self._resolve(observations)

        self.assertEqual(quote.unit_price, Decimal("101.00"))
        self.assertEqual(quote.confidence, Confidence.LOW)
        self.assertEqual(quote.observation_ids, ("new",))

    def test_city_reference_remains_city_precision(self):
        observation = self._observation(
            "city",
            "99.50",
            source_type=SourceType.OFFICIAL_REFERENCE,
            precision=GeographicPrecision.CITY,
        )

        quote = self._resolve([observation])

        self.assertEqual(quote.label, PriceLabel.REFERENCE)
        self.assertEqual(quote.geography_precision, GeographicPrecision.CITY)

    def test_third_party_city_price_does_not_override_station_report(self):
        reference = self._observation(
            "aggregator", "99", source_type=SourceType.THIRD_PARTY_REFERENCE,
            precision=GeographicPrecision.CITY,
        )
        quote = self._resolve([reference])
        self.assertEqual(quote.label, PriceLabel.REFERENCE)
        self.assertEqual(quote.confidence, Confidence.LOW)
        self.assertEqual(quote.geography_precision, GeographicPrecision.CITY)
        reported = self._resolve([reference, self._observation("pump", "101")])
        self.assertEqual(reported.observation_ids, ("pump",))

    def test_expired_value_is_unavailable_by_default(self):
        observation = self._observation(
            "expired", "100", age_hours=3, expires_hours=-1
        )

        quote = self._resolve([observation])

        self.assertEqual(quote.label, PriceLabel.UNAVAILABLE)
        self.assertIsNone(quote.unit_price)

    def test_expired_value_can_only_be_explicitly_stale(self):
        observation = self._observation(
            "expired", "100", age_hours=3, expires_hours=-1
        )

        quote = self._resolve([observation], allow_stale=True)

        self.assertEqual(quote.label, PriceLabel.STALE)
        self.assertEqual(quote.unit_price, Decimal("100"))

    def test_retracted_and_wrong_fuel_observations_are_ignored(self):
        observations = [
            self._observation(
                "retracted",
                "100",
                state=ObservationState.RETRACTED,
            ),
            self._observation("diesel", "90", fuel_type=FuelType.DIESEL),
        ]

        quote = self._resolve(observations)

        self.assertEqual(quote.label, PriceLabel.UNAVAILABLE)

    def _resolve(self, observations, **kwargs):
        return resolve_price_quote(
            observations,
            fuel_type=FuelType.PETROL,
            fuel_grade=None,
            at=self.now,
            **kwargs,
        )

    def _observation(
        self,
        observation_id,
        price,
        *,
        contributor="driver",
        age_hours=1,
        expires_hours=23,
        source_type=SourceType.COMMUNITY_REPORT,
        precision=GeographicPrecision.STATION,
        state=ObservationState.ACCEPTED,
        fuel_type=FuelType.PETROL,
    ):
        observed_at = self.now - timedelta(hours=age_hours)
        return PriceObservationValue(
            observation_id=observation_id,
            station_id="osm-node-1",
            geography_precision=precision,
            geography_id=(
                "osm-node-1"
                if precision == GeographicPrecision.STATION
                else "ahmedabad"
            ),
            fuel_type=fuel_type,
            fuel_grade=None,
            unit_price=Decimal(price),
            source_type=source_type,
            source_id="source",
            observed_at=observed_at,
            effective_at=observed_at,
            received_at=observed_at,
            expires_at=self.now + timedelta(hours=expires_hours),
            state=state,
            contributor_id=contributor,
        )
