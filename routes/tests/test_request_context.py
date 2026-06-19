from django.test import SimpleTestCase
from django.urls import reverse


class RequestContextTests(SimpleTestCase):
    def test_preserves_valid_request_id(self):
        response = self.client.get(
            reverse("health-live"),
            HTTP_X_REQUEST_ID="request-123",
        )

        self.assertEqual(response["X-Request-ID"], "request-123")

    def test_replaces_invalid_request_id(self):
        response = self.client.get(
            reverse("health-live"),
            HTTP_X_REQUEST_ID="invalid request id",
        )

        self.assertNotEqual(response["X-Request-ID"], "invalid request id")
        self.assertEqual(len(response["X-Request-ID"]), 32)
