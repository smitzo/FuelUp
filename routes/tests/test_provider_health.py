from datetime import timedelta

from django.test import TestCase, override_settings
from django.utils import timezone

from routes.application.provider_health import check_circuit, record_outcome
from routes.domain.exceptions import ExternalServiceError
from routes.models import ProviderHealth, SourceRegistry


class ProviderHealthTests(TestCase):
    @override_settings(PROVIDER_CIRCUIT_FAILURES=2, PROVIDER_CIRCUIT_SECONDS=60)
    def test_shared_circuit_opens_then_recovers(self):
        SourceRegistry.objects.create(slug="test")
        now = timezone.now()
        record_outcome("test", error_code="timeout", at=now)
        check_circuit("test", at=now)
        record_outcome("test", error_code="timeout", at=now)
        with self.assertRaises(ExternalServiceError):
            check_circuit("test", at=now)
        check_circuit("test", at=now + timedelta(seconds=61))
        record_outcome("test", at=now + timedelta(seconds=61))
        self.assertEqual(ProviderHealth.objects.get().consecutive_failures, 0)
