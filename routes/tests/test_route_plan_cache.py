from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.core.cache import cache
from django.test import SimpleTestCase, override_settings
from django.utils import timezone

from routes.application.route_plan_cache import get_or_build_route_plan
from routes.domain.fuel_data import (
    Confidence,
    FuelType,
    GeographicPrecision,
    PriceLabel,
    ResolvedPriceQuote,
    RoutePlanRequest,
    VehicleProfile,
)
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

        first = get_or_build_route_plan(self.request, catalogue, self.market, build)
        second = get_or_build_route_plan(self.request, catalogue, self.market, build)

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

    def test_provider_selection_changes_cache_identity(self):
        catalogue = self._catalogue()
        calls = []

        def build():
            calls.append(True)
            return {"build": len(calls)}

        first = get_or_build_route_plan(self.request, catalogue, self.market, build)
        second_market = market_config(routing_source_slug="replacement-router")
        second = get_or_build_route_plan(self.request, catalogue, second_market, build)

        self.assertEqual(first[0]["build"], 1)
        self.assertEqual(second[0]["build"], 2)

    def test_quote_freshness_and_retraction_invalidate_without_new_watermark(self):
        catalogue = self._catalogue()
        now = timezone.now()
        quote = ResolvedPriceQuote(
            unit_price=Decimal("101"),
            label=PriceLabel.REPORTED,
            geography_precision=GeographicPrecision.STATION,
            confidence=Confidence.MEDIUM,
            as_of=now,
            expires_at=now + timedelta(hours=1),
            observation_ids=("price-1",),
        )
        station = SimpleNamespace(stable_id="synthetic-1", price_quote=quote)
        catalogue.stations = (station,)
        for expected in (
            quote,
            replace(quote, label=PriceLabel.STALE),
            ResolvedPriceQuote.unavailable(),
        ):
            station.price_quote = expected
            result, status, _ = get_or_build_route_plan(
                self.request,
                catalogue,
                self.market,
                lambda expected=expected: {"label": expected.label},
            )
            self.assertEqual(status, "MISS")
            self.assertEqual(result["label"], expected.label)
        self.assertEqual(catalogue.observation_watermark, 4)

    @patch("routes.application.route_plan_cache.time.sleep")
    @patch("routes.application.route_plan_cache.cache.add", return_value=False)
    @patch("routes.application.route_plan_cache.cache.get")
    def test_waiting_worker_uses_other_workers_completed_plan(self, get, add, sleep):
        get.side_effect = [None, {"built_by": "other-worker"}]
        builder = Mock()
        result, status, _ = get_or_build_route_plan(
            self.request,
            self._catalogue(),
            self.market,
            builder,
        )
        self.assertEqual(result["built_by"], "other-worker")
        self.assertEqual(status, "HIT")
        builder.assert_not_called()

    @override_settings(ROUTE_CACHE_LOCK_WAIT_SECONDS=0)
    @patch("routes.application.route_plan_cache.cache.add", return_value=False)
    def test_expired_lock_wait_builds_instead_of_hanging(self, add):
        builder = Mock(return_value={"built_by": "waiting-worker"})
        result, status, _ = get_or_build_route_plan(
            self.request,
            self._catalogue(),
            self.market,
            builder,
        )
        self.assertEqual(result["built_by"], "waiting-worker")
        self.assertEqual(status, "MISS")
        builder.assert_called_once()

    @patch("routes.application.route_plan_cache.cache.add", return_value=None)
    def test_unavailable_lock_backend_still_builds_a_current_plan(self, add):
        builder = Mock(return_value={"built_by": "fallback"})
        result, status, _ = get_or_build_route_plan(
            self.request,
            self._catalogue(),
            self.market,
            builder,
        )
        self.assertEqual(result["built_by"], "fallback")
        self.assertEqual(status, "MISS")
        builder.assert_called_once()

    @patch("routes.application.route_plan_cache.cache.delete")
    @patch("routes.application.route_plan_cache.cache.add", return_value=True)
    @patch("routes.application.route_plan_cache.cache.get")
    def test_expired_lock_owner_never_deletes_a_replacement_lock(
        self, get, add, delete
    ):
        get.side_effect = [None, "replacement-worker-token"]
        get_or_build_route_plan(
            self.request,
            self._catalogue(),
            self.market,
            lambda: {"current": True},
        )
        delete.assert_not_called()

    @staticmethod
    def _catalogue(earliest_quote_expiry=None):
        return SimpleNamespace(
            stations=(),
            earliest_quote_expiry=earliest_quote_expiry,
            snapshot_version="test-v1",
            observation_watermark=4,
        )
