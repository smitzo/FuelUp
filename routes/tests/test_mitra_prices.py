from datetime import UTC, datetime, timedelta
from decimal import Decimal

from django.test import SimpleTestCase

from routes.infrastructure.mitra_prices import parse_mitra_prices


class MitraPriceParsingTests(SimpleTestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 26, 8, tzinfo=UTC)
        self.row = {
            "location": "Gujarat",
            "location_type": "state",
            "updated_at": self.now.isoformat(),
            "petrol": {"price": "95.07", "unit": "per_litre"},
        }

    def parse(self):
        return parse_mitra_prices({"status": "ok", "data": [self.row]}, at=self.now)

    def test_preserves_decimal_and_source_time(self):
        price = self.parse()[0]
        self.assertEqual(price.unit_price, Decimal("95.07"))
        self.assertEqual(price.geography_id, "in/gujarat")
        self.assertEqual(price.observed_at, self.now)
        original_expiry = price.expires_at
        later = parse_mitra_prices(
            {"status": "ok", "data": [self.row]}, at=self.now + timedelta(hours=1)
        )[0]
        self.assertEqual(later.expires_at, original_expiry)

    def test_missing_state_cannot_be_guessed_for_city(self):
        self.row.update(location="Ahmedabad", location_type="city")
        with self.assertRaisesMessage(ValueError, "parent state"):
            self.parse()
        self.row["state"] = "Gujarat"
        self.assertEqual(self.parse()[0].geography_id, "in/gujarat/ahmedabad")

    def test_bad_unit_timestamp_price_and_duplicates_are_rejected(self):
        for update in (
            {"updated_at": "2020-01-01T00:00:00Z"},
            {"updated_at": "2026-10-26T08:00:00"},
            {"petrol": {"price": "NaN", "unit": "per_litre"}},
            {"petrol": {"price": "95", "unit": "gallon"}},
        ):
            with self.subTest(update=update):
                original = self.row.copy()
                self.row.update(update)
                with self.assertRaises(ValueError):
                    self.parse()
                self.row = original
        with self.assertRaisesMessage(ValueError, "duplicate"):
            parse_mitra_prices(
                {"status": "ok", "data": [self.row, self.row]}, at=self.now
            )
