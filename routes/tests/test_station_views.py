from unittest.mock import patch

from django.test import SimpleTestCase
from django.urls import reverse

from routes.domain.exceptions import StationNotFoundError
from routes.domain.fuel_data import FuelType


class StationViewTests(SimpleTestCase):
    @patch("routes.api.station_views.search_station_directory")
    def test_list_passes_validated_filters_to_directory(self, search):
        search.return_value = {"api_version": "v2", "stations": []}

        response = self.client.get(
            reverse("station-list-v2"),
            {
                "q": "central fuel",
                "fuel_type": "diesel",
                "fuel_grade": "premium",
                "page": "2",
                "page_size": "10",
            },
        )

        self.assertEqual(response.status_code, 200)
        call = search.call_args
        self.assertEqual(call.kwargs["query"], "central fuel")
        self.assertEqual(call.kwargs["fuel_type"], FuelType.DIESEL)
        self.assertEqual(call.kwargs["fuel_grade"], "premium")
        self.assertEqual(call.kwargs["page"], 2)
        self.assertEqual(call.kwargs["page_size"], 10)

    @patch("routes.api.station_views.search_station_directory")
    def test_list_rejects_invalid_or_unexpected_filters(self, search):
        cases = (
            {"page": "0"},
            {"page_size": "51"},
            {"fuel_type": "hydrogen"},
            {"private": "true"},
        )
        for query in cases:
            with self.subTest(query=query):
                response = self.client.get(reverse("station-list-v2"), query)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json()["error"]["code"], "invalid_request")
        search.assert_not_called()

    @patch("routes.api.station_views.get_station_detail")
    def test_detail_returns_typed_not_found_error(self, detail):
        detail.side_effect = StationNotFoundError("Station not found.")

        response = self.client.get(reverse("station-detail-v2", args=("station-404",)))

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "station_not_found")

    def test_station_endpoints_are_read_only(self):
        list_response = self.client.post(reverse("station-list-v2"))
        detail_response = self.client.post(
            reverse("station-detail-v2", args=("station-a",))
        )

        self.assertEqual(list_response.status_code, 405)
        self.assertEqual(detail_response.status_code, 405)
