import json
from unittest.mock import patch

from django.core.cache import cache
from django.test import SimpleTestCase
from django.urls import reverse

from routes.infrastructure.priced_station_repository import (
    StationCatalogue,
)


class RoutePlanV2ViewTests(SimpleTestCase):
    def setUp(self):
        cache.clear()
        self.catalogue = StationCatalogue(
            market_code="IN",
            stations=(),
            snapshot_version="india-test-v1",
            snapshot_generated_at=None,
            observation_watermark=0,
            attribution="Test fixture",
        )
        self.payload = {
            "start": "Ahmedabad, Gujarat",
            "finish": "Vadodara, Gujarat",
            "waypoints": ["Anand, Gujarat"],
            "vehicle": {
                "fuel_type": "petrol",
                "tank_capacity": 35,
                "efficiency": 18,
                "starting_fuel": 8,
                "reserve_fuel": 3,
            },
            "maximum_detour": 5,
            "strategy": "balanced",
            "price_quality": "best_available",
        }

    @patch("routes.api.v2_views.PricedStationRepository.load")
    @patch(
        "routes.api.v2_views.build_route_plan",
        return_value={"api_version": "v2", "market": {"code": "IN"}},
    )
    def test_returns_cached_v2_plan(self, planner, load_catalogue):
        load_catalogue.return_value = self.catalogue

        first = self._post(self.payload)
        second = self._post(self.payload)

        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json()["market"]["code"], "IN")
        self.assertEqual(first["X-FuelUp-Cache"], "MISS")
        self.assertEqual(second["X-FuelUp-Cache"], "HIT")
        planner.assert_called_once()
        route_request = planner.call_args.args[0]
        self.assertEqual(route_request.vehicle.fuel_type, "petrol")
        self.assertEqual(route_request.waypoints, ("Anand, Gujarat",))

    def test_rejects_invalid_vehicle_before_provider_work(self):
        payload = {**self.payload, "vehicle": {**self.payload["vehicle"]}}
        payload["vehicle"]["reserve_fuel"] = 40

        with patch("routes.api.v2_views.PricedStationRepository.load") as load:
            response = self._post(payload)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "invalid_request")
        load.assert_not_called()

    def test_rejects_unknown_fields(self):
        response = self._post({**self.payload, "country": "US"})

        self.assertEqual(response.status_code, 400)
        self.assertIn("Unexpected request fields", response.json()["error"]["message"])

    def test_rejects_non_finite_decimal(self):
        payload = {**self.payload, "vehicle": {**self.payload["vehicle"]}}
        payload["vehicle"]["tank_capacity"] = "NaN"

        response = self._post(payload)

        self.assertEqual(response.status_code, 400)
        self.assertIn("finite", response.json()["error"]["message"])

    @patch("routes.api.v2_views.PricedStationRepository.load")
    @patch("routes.api.v2_views.build_route_plan")
    def test_rejects_missing_market_snapshot_before_provider_work(
        self, planner, load_catalogue
    ):
        load_catalogue.return_value = StationCatalogue.empty("IN")

        response = self._post(self.payload)

        self.assertEqual(response.status_code, 422)
        self.assertEqual(
            response.json()["error"]["code"],
            "insufficient_price_data",
        )
        planner.assert_not_called()

    def _post(self, payload):
        return self.client.post(
            reverse("route-plan-v2"),
            data=json.dumps(payload),
            content_type="application/json",
        )
