from datetime import datetime

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from routes.application.contributor_privacy import rate_limit_subject_hash
from routes.domain.exceptions import (
    ContributionRateLimitError,
    ContributionUnavailableError,
)


def enforce_contribution_rate_limits(
    identity,
    *,
    market_code: str,
    station_id: str,
    at: datetime | None = None,
):
    at = at or timezone.now()
    window = settings.CONTRIBUTION_RATE_LIMIT_WINDOW_SECONDS
    limits = settings.CONTRIBUTION_RATE_LIMITS
    if window <= 0 or any(value <= 0 for value in limits.values()):
        raise ContributionUnavailableError(
            "Contribution abuse controls are not configured safely."
        )
    subjects = {
        "network": identity.network_hash,
        "device": identity.device_hash,
        "contributor": identity.contributor_id,
        "station": rate_limit_subject_hash("station", market_code, station_id),
    }
    bucket = int(at.timestamp()) // window
    retry_after = max(1, ((bucket + 1) * window) - int(at.timestamp()))
    for dimension, subject_hash in subjects.items():
        _increment_or_reject(
            dimension=dimension,
            subject_hash=subject_hash,
            bucket=bucket,
            limit=limits[dimension],
            timeout=window + 1,
            retry_after=retry_after,
        )


def _increment_or_reject(
    *,
    dimension,
    subject_hash,
    bucket,
    limit,
    timeout,
    retry_after,
):
    key = f"fuelup:contribution-limit:v1:{dimension}:{subject_hash}:{bucket}"
    try:
        added = cache.add(key, 1, timeout=timeout)
        if added is True:
            count = 1
        elif added is False:
            count = cache.incr(key)
        else:
            raise RuntimeError("Cache did not confirm the rate-limit write.")
        if not isinstance(count, int):
            raise RuntimeError("Cache returned an invalid rate-limit count.")
    except Exception as exc:
        raise ContributionUnavailableError(
            "Contribution abuse controls are temporarily unavailable."
        ) from exc
    if count > limit:
        raise ContributionRateLimitError(
            f"The {dimension} contribution limit has been reached.",
            retry_after=retry_after,
        )
