from datetime import UTC, datetime
from unittest.mock import patch

from django.core.cache import cache
from django.test import SimpleTestCase, override_settings

from routes.application.contribution_rate_limit import (
    enforce_contribution_rate_limits,
)
from routes.application.contributor_privacy import ContributorIdentity
from routes.domain.exceptions import (
    ContributionRateLimitError,
    ContributionUnavailableError,
)


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "contribution-limit-tests",
        }
    },
    CONTRIBUTION_HASH_SECRET="test-only-contribution-secret",
    CONTRIBUTION_RATE_LIMIT_WINDOW_SECONDS=60,
    CONTRIBUTION_RATE_LIMITS={
        "network": 10,
        "device": 10,
        "contributor": 10,
        "station": 1,
    },
)
class ContributionRateLimitTests(SimpleTestCase):
    def setUp(self):
        cache.clear()
        self.identity = ContributorIdentity(
            contributor_id="a" * 64,
            device_hash="b" * 64,
            network_hash="c" * 64,
            rotation_period="2026-08",
        )
        self.now = datetime(2026, 8, 10, 12, 0, 30, tzinfo=UTC)

    def test_limits_each_station_with_hashed_cache_keys(self):
        values = {
            "market_code": "GB",
            "station_id": "station-a",
            "at": self.now,
        }
        enforce_contribution_rate_limits(self.identity, **values)

        with self.assertRaises(ContributionRateLimitError) as caught:
            enforce_contribution_rate_limits(self.identity, **values)

        self.assertEqual(caught.exception.retry_after, 30)
        self.assertNotIn("station-a", repr(cache._cache))

    @patch("routes.application.contribution_rate_limit.cache.add", return_value=None)
    def test_fails_closed_when_cache_cannot_confirm_write(self, _add):
        with self.assertRaises(ContributionUnavailableError):
            enforce_contribution_rate_limits(
                self.identity,
                market_code="GB",
                station_id="station-a",
                at=self.now,
            )
