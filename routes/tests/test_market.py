from decimal import Decimal

from django.test import SimpleTestCase, override_settings

from routes.application.market import get_market_config
from routes.domain.market import MarketConfig
from routes.tests.factories import market_config


class MarketConfigTests(SimpleTestCase):
    def test_normalizes_codes_and_declares_response_units(self):
        market = market_config(code="in", country_code="IN", currency_code="inr")

        self.assertEqual(market.code, "IN")
        self.assertEqual(market.country_code, "in")
        self.assertEqual(
            market.response_metadata(),
            {
                "code": "IN",
                "country_code": "in",
                "country_name": "India",
                "currency_code": "INR",
                "distance_unit": "km",
                "volume_unit": "litre",
                "efficiency_unit": "km/litre",
            },
        )

    def test_rejects_invalid_currency_or_conversion(self):
        with self.assertRaisesRegex(ValueError, "Currency"):
            market_config(currency_code="rupees")
        with self.assertRaisesRegex(ValueError, "conversion"):
            market_config(distance_units_per_mile=Decimal("0"))

    @override_settings(
        MARKET_CONFIG={
            "code": "ZZ",
            "country_code": "zz",
            "country_name": "Testland",
            "country_geography_id": "testland",
            "currency_code": "TST",
            "distance_unit": "distance-unit",
            "volume_unit": "volume-unit",
            "efficiency_unit": "distance/volume",
            "distance_units_per_mile": 2,
            "time_value_per_hour": 3,
            "stop_penalty": 4,
            "route_cache_seconds": 5,
            "station_source_slug": "stations",
            "geocoding_source_slug": "geocoder",
            "routing_source_slug": "router",
        }
    )
    def test_builds_market_from_settings_without_product_specific_code(self):
        market = get_market_config()

        self.assertIsInstance(market, MarketConfig)
        self.assertEqual(market.code, "ZZ")
        self.assertEqual(market.currency_code, "TST")
        self.assertEqual(market.distance_units_per_mile, Decimal("2"))
