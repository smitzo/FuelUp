import json
from unittest.mock import patch

from django.conf import settings
from django.core.cache import cache
from django.test import SimpleTestCase
from django.urls import reverse

from routes.domain.exceptions import LocationNotFoundError


class RoutePlanViewTests(SimpleTestCase):
    def setUp(self):
        cache.clear()

    def test_rejects_invalid_json(self):
        response = self.client.post(
            reverse("route-plan"),
            data="{",
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "invalid_request")

    def test_requires_start_and_finish_strings(self):
        response = self.client.post(
            reverse("route-plan"),
            data=json.dumps({"start": "", "finish": "Austin, TX"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('"start"', response.json()["error"]["message"])

    @patch(
        "routes.api.views.build_route_plan",
        return_value={"route": {"distance_miles": 1}},
    )
    def test_returns_route_plan(self, planner):
        response = self.client.post(
            reverse("route-plan"),
            data=json.dumps({"start": "Austin, TX", "finish": "Dallas, TX"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["route"]["distance_miles"], 1)
        self.assertEqual(response["X-FuelUp-Cache"], "MISS")
        self.assertEqual(
            response["X-FuelUp-Cache-TTL"],
            str(settings.ROUTE_CACHE_SECONDS),
        )
        planner.assert_called_once_with("Austin, TX", "Dallas, TX")

    @patch(
        "routes.api.views.build_route_plan",
        return_value={"route": {"distance_miles": 1}},
    )
    def test_returns_cached_route_plan(self, planner):
        payload = json.dumps(
            {"start": "Austin, TX", "finish": "Dallas, TX"}
        )

        first = self.client.post(
            reverse("route-plan"),
            data=payload,
            content_type="application/json",
        )
        second = self.client.post(
            reverse("route-plan"),
            data=payload,
            content_type="application/json",
        )

        self.assertEqual(first["X-FuelUp-Cache"], "MISS")
        self.assertEqual(second["X-FuelUp-Cache"], "HIT")
        planner.assert_called_once()

    @patch(
        "routes.api.views.build_route_plan",
        side_effect=LocationNotFoundError("Location was not found."),
    )
    def test_returns_structured_domain_error(self, planner):
        response = self.client.post(
            reverse("route-plan"),
            data=json.dumps({"start": "Unknown", "finish": "Dallas, TX"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["error"]["code"], "location_not_found")
