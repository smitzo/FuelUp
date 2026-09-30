from django.db.models import Count, Min
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET

from routes.application.market import get_market_config
from routes.models import PriceObservation, ProviderHealth, StationSnapshot


@require_GET
def data_status(request):
    """Public aggregate coverage only; never expose contributor or credential data."""
    market = get_market_config()
    snapshot = StationSnapshot.objects.filter(
        market_code=market.code, is_active=True, is_valid=True
    ).first()
    current = PriceObservation.objects.filter(
        market_code=market.code,
        state="accepted",
        expires_at__gt=timezone.now(),
        effective_at__lte=timezone.now(),
        source__enabled=True,
    )
    scopes = list(
        current.values("geography_precision", "fuel_type").annotate(
            observations=Count("id"), oldest_observed_at=Min("observed_at")
        )
    )
    response = JsonResponse(
        {
            "market": market.response_metadata(),
            "catalogue": {
                "available": snapshot is not None,
                "version": snapshot.version if snapshot else None,
                "generated_at": snapshot.source_generated_at if snapshot else None,
                "stations": snapshot.stations.count() if snapshot else 0,
            },
            "current_price_scopes": scopes,
            "providers": list(
                ProviderHealth.objects.values(
                    "source_id", "last_success_at", "blocked_until", "last_error_code"
                )
            ),
            "as_of": timezone.now(),
        }
    )
    response["Cache-Control"] = "public, max-age=60"
    return response
