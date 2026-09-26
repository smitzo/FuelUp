import io
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from routes.domain.exceptions import ExternalServiceError
from routes.infrastructure.provider_http import NoRedirect, request_json


class ProviderHttpTests(SimpleTestCase):
    def test_unsafe_url_is_rejected_before_budget_or_network(self):
        with self.assertRaises(ExternalServiceError):
            request_json("test", "http://example.com", "/fuel")
        self.assertIsNone(NoRedirect().redirect_request(None, None, 302, "", {}, "x"))

    @patch("routes.infrastructure.provider_http.record_outcome")
    @patch("routes.infrastructure.provider_http.reserve_request")
    @patch("routes.infrastructure.provider_http.check_circuit")
    @patch("urllib.request.OpenerDirector.open")
    def test_valid_json_and_no_credential_echo(
        self, network, circuit, reserve, outcome
    ):
        network.return_value = io.BytesIO(b'{"price": 101.05}')
        result = request_json(
            "test", "https://example.com", "/fuel", headers={"x-api-key": "test-secret"}
        )
        self.assertEqual(result["price"], "101.05")
        reserve.assert_called_once_with("test")
        outcome.assert_called_once_with("test", error_code="")

    @override_settings(PROVIDER_MAX_RESPONSE_BYTES=4)
    @patch("routes.infrastructure.provider_http.record_outcome")
    @patch("routes.infrastructure.provider_http.reserve_request")
    @patch("routes.infrastructure.provider_http.check_circuit")
    @patch("urllib.request.OpenerDirector.open")
    def test_oversized_response_is_a_typed_error(self, network, *mocks):
        network.return_value = io.BytesIO(b'{"too":"large"}')
        with self.assertRaisesMessage(ExternalServiceError, "invalid_response"):
            request_json("test", "https://example.com", "/fuel")
