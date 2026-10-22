import io
import urllib.error
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from routes.models import (
    PriceImportBatch,
    ProviderHealth,
    ProviderUsage,
    SourceRegistry,
)
from routes.tests.test_provider_price_import import ProviderPriceImportTests


class RefreshPricesTests(TestCase):
    @patch("routes.management.commands.refresh_prices.MitraPriceClient.snapshot")
    def test_disabled_source_makes_no_network_call(self, fetch):
        with self.assertRaises(CommandError):
            call_command("refresh_prices", stdout=StringIO())
        fetch.assert_not_called()

    @patch("routes.management.commands.refresh_prices.MitraPriceClient.snapshot")
    def test_repeated_scheduler_run_does_not_refetch(self, fetch):
        fixture = ProviderPriceImportTests()
        fixture.setUp()
        fetch.return_value = ({}, [fixture.price])
        call_command("refresh_prices", stdout=StringIO())
        call_command("refresh_prices", stdout=StringIO())
        fetch.assert_called_once()
        SourceRegistry.objects.filter(slug="api-mitra-fuel").update(enabled=False)
        with self.assertRaises(CommandError):
            call_command("refresh_prices", force=True, stdout=StringIO())


@override_settings(
    API_MITRA_API_KEY="synthetic-key",
    PROVIDER_MONTHLY_LIMITS={"api-mitra-fuel": 10},
    PROVIDER_DAILY_LIMITS={"api-mitra-fuel": 10},
    PROVIDER_MINUTE_LIMITS={"api-mitra-fuel": 10},
    PROVIDER_CIRCUIT_FAILURES=3,
)
class RefreshFailureAccountingTests(TestCase):
    def setUp(self):
        fixture = ProviderPriceImportTests()
        fixture.setUp()
        fixture.source.refresh_budget_per_day = 10
        fixture.source.save(update_fields=("refresh_budget_per_day",))

    @patch("urllib.request.OpenerDirector.open")
    def test_failed_refresh_keeps_charges_and_opens_circuit(self, network):
        network.side_effect = urllib.error.URLError("synthetic transport failure")
        for _ in range(4):
            with self.assertRaises(CommandError):
                call_command("refresh_prices", stdout=StringIO())
        self.assertEqual(network.call_count, 3)
        self.assertEqual(
            set(ProviderUsage.objects.values_list("requests", flat=True)), {3}
        )
        self.assertEqual(ProviderUsage.objects.count(), 3)
        health = ProviderHealth.objects.get(source_id="api-mitra-fuel")
        self.assertEqual(health.consecutive_failures, 3)
        self.assertIsNotNone(health.blocked_until)
        self.assertEqual(health.last_error_code, "network_error")
        self.assertFalse(PriceImportBatch.objects.exists())

    @patch("urllib.request.OpenerDirector.open")
    def test_invalid_price_payload_still_consumes_transport_quota(self, network):
        network.return_value = io.BytesIO(b'{"invalid": "synthetic payload"}')
        with self.assertRaises(CommandError):
            call_command("refresh_prices", stdout=StringIO())
        self.assertEqual(ProviderUsage.objects.count(), 3)
        self.assertEqual(
            set(ProviderUsage.objects.values_list("requests", flat=True)), {1}
        )
        self.assertIsNotNone(
            ProviderHealth.objects.get(source_id="api-mitra-fuel").last_success_at
        )
        self.assertFalse(PriceImportBatch.objects.exists())
