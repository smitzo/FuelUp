import threading
import time
from unittest.mock import patch

from django.core.cache import cache
from django.test import SimpleTestCase, override_settings

from routes.application.plan_cache import get_or_build_route_plan


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        }
    },
    ROUTE_CACHE_SECONDS=60,
    ROUTE_CACHE_LOCK_WAIT_SECONDS=1,
    ROUTE_GEOMETRY_OVERVIEW="simplified",
)
class RoutePlanCacheTests(SimpleTestCase):
    def setUp(self):
        cache.clear()

    def test_reuses_normalized_route_request(self):
        calls = []

        def builder(start, finish):
            calls.append((start, finish))
            return {"route": {"distance_miles": 100}}

        first, first_status = get_or_build_route_plan(
            " Austin,   TX ",
            "DALLAS, TX",
            builder,
        )
        second, second_status = get_or_build_route_plan(
            "austin, tx",
            "dallas, tx",
            builder,
        )

        self.assertEqual(first, second)
        self.assertEqual(first_status, "MISS")
        self.assertEqual(second_status, "HIT")
        self.assertEqual(len(calls), 1)

    def test_does_not_cache_builder_errors(self):
        calls = 0

        def builder(start, finish):
            nonlocal calls
            calls += 1
            raise RuntimeError("provider failed")

        for _ in range(2):
            with self.assertRaises(RuntimeError):
                get_or_build_route_plan("Austin", "Dallas", builder)

        self.assertEqual(calls, 2)

    def test_concurrent_request_reuses_in_flight_result(self):
        builder_started = threading.Event()
        release_builder = threading.Event()
        results = []
        calls = 0

        def builder(start, finish):
            nonlocal calls
            calls += 1
            builder_started.set()
            release_builder.wait(timeout=1)
            return {"route": {"distance_miles": 100}}

        first = threading.Thread(
            target=lambda: results.append(
                get_or_build_route_plan("Austin", "Denver", builder)
            )
        )
        second = threading.Thread(
            target=lambda: results.append(
                get_or_build_route_plan("Austin", "Denver", builder)
            )
        )

        first.start()
        self.assertTrue(builder_started.wait(timeout=1))
        second.start()
        time.sleep(0.1)
        release_builder.set()
        first.join(timeout=1)
        second.join(timeout=1)

        self.assertEqual(calls, 1)
        self.assertEqual(sorted(status for _, status in results), ["HIT", "MISS"])

    @patch("routes.application.plan_cache.cache.set")
    @patch("routes.application.plan_cache.cache.add", return_value=None)
    @patch("routes.application.plan_cache.cache.get", return_value=None)
    def test_cache_outage_does_not_wait_for_lock(
        self,
        cache_get,
        cache_add,
        cache_set,
    ):
        started = time.monotonic()

        result, status = get_or_build_route_plan(
            "Austin",
            "Denver",
            lambda start, finish: {"route": {}},
        )

        self.assertEqual(result, {"route": {}})
        self.assertEqual(status, "MISS")
        self.assertLess(time.monotonic() - started, 0.1)
        cache_get.assert_called_once()
        cache_add.assert_called_once()
        cache_set.assert_called_once()
