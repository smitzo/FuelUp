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
