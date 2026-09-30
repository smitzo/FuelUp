from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from routes.models import SourceRegistry
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
