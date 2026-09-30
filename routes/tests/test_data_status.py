from django.test import TestCase


class DataStatusTests(TestCase):
    def test_empty_market_is_explicit_and_contains_no_secrets(self):
        response = self.client.get("/api/v2/data-status/")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["market"]["code"], "IN")
        self.assertFalse(payload["catalogue"]["available"])
        self.assertEqual(payload["current_price_scopes"], [])
        self.assertNotIn("key", response.content.decode().casefold())
