from datetime import UTC

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from routes.domain.exceptions import ExternalServiceError
from routes.models import ProviderUsage, SourceRegistry


class ProviderBudgetExceeded(ExternalServiceError):
    code = "provider_budget_exceeded"
    status = 503


@transaction.atomic
def reserve_request(source_slug, *, at=None):
    """Charge every attempted request, before network I/O; never refund failures."""
    at = (at or timezone.now()).astimezone(UTC)
    source = SourceRegistry.objects.select_for_update().get(slug=source_slug)
    if not source.can_fetch:
        raise ExternalServiceError("This provider is disabled by the source registry.")
    windows = (
        (
            "minute",
            at.replace(second=0, microsecond=0),
            settings.PROVIDER_MINUTE_LIMITS.get(source_slug, 0),
        ),
        (
            "day",
            at.replace(hour=0, minute=0, second=0, microsecond=0),
            min(
                settings.PROVIDER_DAILY_LIMITS.get(source_slug, 0),
                source.refresh_budget_per_day,
            ),
        ),
        (
            "month",
            at.replace(day=1, hour=0, minute=0, second=0, microsecond=0),
            settings.PROVIDER_MONTHLY_LIMITS.get(source_slug, 0),
        ),
    )
    counters = []
    for period, start, limit in windows:
        if limit <= 0:
            raise ProviderBudgetExceeded("Provider quota is not configured.")
        usage, _ = ProviderUsage.objects.get_or_create(
            source=source, period=period, window_start=start
        )
        if usage.requests >= limit:
            raise ProviderBudgetExceeded("Provider request allowance is exhausted.")
        counters.append(usage)
    for usage in counters:
        usage.requests += 1
        usage.save(update_fields=("requests",))
