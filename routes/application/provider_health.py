from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from routes.domain.exceptions import ExternalServiceError
from routes.models import ProviderHealth, SourceRegistry


def check_circuit(source_slug, *, at=None):
    state = ProviderHealth.objects.filter(source_id=source_slug).first()
    if state and state.blocked_until and state.blocked_until > (at or timezone.now()):
        raise ExternalServiceError(
            "This provider is temporarily paused after failures."
        )


@transaction.atomic
def record_outcome(source_slug, *, error_code="", at=None):
    at = at or timezone.now()
    source = SourceRegistry.objects.select_for_update().get(slug=source_slug)
    state, _ = ProviderHealth.objects.get_or_create(source=source)
    if error_code:
        state.consecutive_failures += 1
        state.last_failure_at = at
        state.last_error_code = error_code[:50]
        if state.consecutive_failures >= settings.PROVIDER_CIRCUIT_FAILURES:
            state.blocked_until = at + timedelta(
                seconds=settings.PROVIDER_CIRCUIT_SECONDS
            )
    else:
        state.consecutive_failures = 0
        state.blocked_until = None
        state.last_success_at = at
        state.last_error_code = ""
    state.save()
