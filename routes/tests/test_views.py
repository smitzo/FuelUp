import json
from unittest.mock import patch

from django.test import SimpleTestCase
from django.urls import reverse

from routes.exceptions import LocationNotFoundError


class RoutePlanViewTests(SimpleTestCase):
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

    @patch("routes.views.build_route_plan", return_value={"route": {"distance_miles": 1}})
    def test_returns_route_plan(self, planner):
        response = self.client.post(
            reverse("route-plan"),
            data=json.dumps({"start": "Austin, TX", "finish": "Dallas, TX"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["route"]["distance_miles"], 1)
        planner.assert_called_once_with("Austin, TX", "Dallas, TX")

    @patch(
        "routes.views.build_route_plan",
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
