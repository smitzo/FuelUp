from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace

from django.core.cache import cache
from django.test import SimpleTestCase, override_settings
from django.utils import timezone

from routes.application.route_plan_cache import get_or_build_route_plan
from routes.domain.fuel_data import FuelType, RoutePlanRequest, VehicleProfile
from routes.tests.factories import market_config


@override_settings(
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
)
class RoutePlanCacheTests(SimpleTestCase):
    def setUp(self):
        cache.clear()
        self.market = market_config(route_cache_seconds=3600)
        self.request = RoutePlanRequest(
            start="Ahmedabad",
            finish="Vadodara",
            waypoints=(),
            vehicle=VehicleProfile(
                fuel_type=FuelType.PETROL,
                tank_capacity=Decimal("35"),
                efficiency=Decimal("18"),
                starting_fuel=Decimal("8"),
                reserve_fuel=Decimal("3"),
            ),
            maximum_detour=Decimal("5"),
        )

    def test_reuses_plan_for_same_market_and_catalogue_versions(self):
        catalogue = self._catalogue()
        calls = []

        def build():
            calls.append(True)
            return {"api_version": "v2"}

        first = get_or_build_route_plan(
            self.request, catalogue, self.market, build
        )
        second = get_or_build_route_plan(
            self.request, catalogue, self.market, build
        )

        self.assertEqual(first[1], "MISS")
        self.assertEqual(second[1], "HIT")
        self.assertEqual(len(calls), 1)

    def test_bounds_cache_lifetime_by_quote_expiry(self):
        catalogue = self._catalogue(
            earliest_quote_expiry=timezone.now() + timedelta(seconds=30)
        )

        _, _, ttl = get_or_build_route_plan(
            self.request,
            catalogue,
            self.market,
            lambda: {"api_version": "v2"},
        )

        self.assertLessEqual(ttl, 30)
        self.assertGreater(ttl, 0)

    @staticmethod
    def _catalogue(earliest_quote_expiry=None):
        return SimpleNamespace(
            earliest_quote_expiry=earliest_quote_expiry,
            snapshot_version="test-v1",
            observation_watermark=4,
        )
