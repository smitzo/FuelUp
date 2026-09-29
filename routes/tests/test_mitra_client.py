from unittest.mock import patch

from django.test import SimpleTestCase, override_settings
from django.utils import timezone

from routes.domain.exceptions import ExternalServiceError
from routes.infrastructure.mitra_client import MitraPriceClient


class MitraClientTests(SimpleTestCase):
    @override_settings(API_MITRA_API_KEY="")
    @patch("routes.infrastructure.mitra_client.request_json")
    def test_missing_key_is_local_failure(self, request):
        with self.assertRaises(ExternalServiceError):
            MitraPriceClient().snapshot()
        request.assert_not_called()

    @override_settings(API_MITRA_API_KEY="not-a-real-key")
    @patch("routes.infrastructure.mitra_client.request_json")
    def test_authentication_and_source_timestamp(self, request):
        request.return_value = {
            "status": "ok",
            "data": [
                {
                    "location": "Gujarat",
                    "location_type": "state",
                    "updated_at": timezone.now().isoformat(),
                    "petrol": {"price": "95.07", "unit": "per_litre"},
                }
            ],
        }
        _, prices = MitraPriceClient().snapshot()
        self.assertEqual(prices[0].geography_id, "in/gujarat")
        self.assertEqual(
            request.call_args.kwargs["headers"], {"x-api-key": "not-a-real-key"}
        )
        request.return_value = {"status": "error"}
        with self.assertRaises(ExternalServiceError):
            MitraPriceClient().snapshot()
