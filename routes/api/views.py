import json

from django.conf import settings
from django.core.cache import cache
from django.db import DatabaseError
from django.db.models import Q
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from routes.application.market import get_market_config
from routes.application.plan_cache import get_or_build_route_plan
from routes.application.planner import build_route_plan
from routes.domain.exceptions import InvalidRequestError, RoutePlannerError
from routes.domain.fuel_data import ObservationState
from routes.models import PriceObservation, StationFuel, StationSnapshot


@require_GET
def health(request):
    return JsonResponse(
        {
            "status": "ok",
            "service": "fuelup-api",
            "release": settings.RELEASE_SHA,
        }
    )


@require_GET
def readiness(request):
    checks = {
        "station_prices": _market_data_ready(),
        "cache": _cache_ready(),
    }
    ready = all(checks.values())
    return JsonResponse(
        {
            "status": "ready" if ready else "not_ready",
            "checks": checks,
            "release": settings.RELEASE_SHA,
        },
        status=200 if ready else 503,
    )


@csrf_exempt
@require_POST
def route_plan(request):
    try:
        payload = _json_body(request)
        start = _location_value(payload, "start")
        finish = _location_value(payload, "finish")
        plan, cache_status = get_or_build_route_plan(
            start,
            finish,
            builder=build_route_plan,
        )
        response = JsonResponse(plan)
        response["X-FuelUp-Cache"] = cache_status
        response["X-FuelUp-Cache-TTL"] = str(settings.ROUTE_CACHE_SECONDS)
        return response
    except RoutePlannerError as exc:
        return JsonResponse(
            {"error": {"code": exc.code, "message": exc.message}},
            status=exc.status,
        )


def _json_body(request):
    try:
        payload = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise InvalidRequestError("Request body must be valid JSON.") from exc
    if not isinstance(payload, dict):
        raise InvalidRequestError("Request body must be a JSON object.")
    return payload


def _location_value(payload, key):
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise InvalidRequestError(f'"{key}" must be a non-empty string.')
    if len(value) > 300:
        raise InvalidRequestError(f'"{key}" must be 300 characters or fewer.')
    return value.strip()


def _market_data_ready():
    try:
        market = get_market_config()
        snapshot = StationSnapshot.objects.filter(
            market_code=market.code,
            is_active=True,
            is_valid=True,
        ).first()
        if snapshot is None:
            return False
        fuel_types = StationFuel.objects.filter(
            station__snapshot=snapshot,
            is_available=True,
        ).values("fuel_type")
        now = timezone.now()
        return PriceObservation.objects.filter(
            Q(station__snapshot=snapshot) | Q(station__isnull=True),
            market_code=market.code,
            fuel_type__in=fuel_types,
            state=ObservationState.ACCEPTED,
            effective_at__lte=now,
            expires_at__gt=now,
        ).exists()
    except DatabaseError:
        return False


def _cache_ready():
    key = "fuelup:readiness"
    try:
        cache.set(key, "ok", timeout=5)
        ready = cache.get(key) == "ok"
        cache.delete(key)
        return ready
    except Exception:
        return False
