from django.test import TestCase, override_settings


class RequestSizeTests(TestCase):
    @override_settings(DATA_UPLOAD_MAX_MEMORY_SIZE=256)
    def test_oversized_route_fails_with_typed_413(self):
        response = self.client.post(
            "/api/v2/route/", data="x" * 257, content_type="application/json"
        )
        self.assertEqual(response.status_code, 413)
        self.assertEqual(response.json()["error"]["code"], "request_too_large")
