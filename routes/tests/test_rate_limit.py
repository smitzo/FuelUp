import json
from unittest.mock import patch

from django.core.cache import cache
from django.test import SimpleTestCase, override_settings
from django.urls import reverse


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        }
    },
    ROUTE_RATE_LIMIT_REQUESTS=2,
    ROUTE_RATE_LIMIT_WINDOW_SECONDS=60,
)
class RouteRateLimitTests(SimpleTestCase):
    def setUp(self):
        cache.clear()

    @patch(
        "routes.api.views.build_route_plan",
        return_value={"route": {"distance_miles": 1}},
    )
    def test_limits_route_requests_by_client(self, planner):
        payload = json.dumps(
            {"start": "Austin, TX", "finish": "Dallas, TX"}
        )
        responses = [
            self.client.post(
                reverse("route-plan"),
                data=payload,
                content_type="application/json",
                REMOTE_ADDR="203.0.113.10",
            )
            for _ in range(3)
        ]

        self.assertEqual(
            [response.status_code for response in responses],
            [200, 200, 429],
        )
        self.assertEqual(responses[0]["X-RateLimit-Remaining"], "1")
        self.assertEqual(responses[2]["X-RateLimit-Remaining"], "0")
        self.assertIn("Retry-After", responses[2])

    @patch(
        "routes.api.views.build_route_plan",
        return_value={"route": {"distance_miles": 1}},
    )
    def test_clients_have_independent_quotas(self, planner):
        payload = json.dumps(
            {"start": "Austin, TX", "finish": "Dallas, TX"}
        )
        first = self.client.post(
            reverse("route-plan"),
            data=payload,
            content_type="application/json",
            REMOTE_ADDR="203.0.113.10",
        )
        second = self.client.post(
            reverse("route-plan"),
            data=payload,
            content_type="application/json",
            REMOTE_ADDR="203.0.113.11",
        )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
