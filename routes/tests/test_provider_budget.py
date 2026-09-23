from datetime import timedelta

from django.test import TestCase, override_settings
from django.utils import timezone

from routes.application.provider_budget import ProviderBudgetExceeded, reserve_request
from routes.models import ProviderUsage, SourceRegistry


@override_settings(
    PROVIDER_MINUTE_LIMITS={"test": 2},
    PROVIDER_DAILY_LIMITS={"test": 3},
    PROVIDER_MONTHLY_LIMITS={"test": 4},
)
class ProviderBudgetTests(TestCase):
    def setUp(self):
        self.source = SourceRegistry.objects.create(
            slug="test",
            enabled=True,
            automated_access_allowed=True,
            refresh_budget_per_day=3,
        )
        self.now = timezone.now().replace(second=0, microsecond=0)

    def test_exhaustion_does_not_partially_charge_other_windows(self):
        reserve_request("test", at=self.now)
        reserve_request("test", at=self.now)
        with self.assertRaises(ProviderBudgetExceeded):
            reserve_request("test", at=self.now)
        self.assertEqual(
            set(ProviderUsage.objects.values_list("requests", flat=True)), {2}
        )
        reserve_request("test", at=self.now + timedelta(minutes=1))
        with self.assertRaises(ProviderBudgetExceeded):
            reserve_request("test", at=self.now + timedelta(minutes=2))

    @override_settings(PROVIDER_MONTHLY_LIMITS={})
    def test_missing_quota_is_a_hard_stop(self):
        with self.assertRaises(ProviderBudgetExceeded):
            reserve_request("test", at=self.now)
        self.assertFalse(ProviderUsage.objects.exists())
