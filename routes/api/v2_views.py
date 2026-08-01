import json
from decimal import Decimal, InvalidOperation

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from routes.application.market import get_market_config
from routes.application.market_planner import build_route_plan
from routes.application.route_plan_cache import get_or_build_route_plan
from routes.domain.exceptions import (
    ApiError,
    InsufficientPriceDataError,
    InvalidRequestError,
)
from routes.domain.fuel_data import (
    FuelType,
    PriceQualityPolicy,
    RoutePlanRequest,
    RouteStrategy,
    VehicleProfile,
)
from routes.infrastructure.priced_station_repository import (
    PricedStationRepository,
)

REQUEST_FIELDS = {
    "start",
    "finish",
    "waypoints",
    "vehicle",
    "maximum_detour",
    "strategy",
    "price_quality",
    "allow_stale_prices",
}
VEHICLE_FIELDS = {
    "fuel_type",
    "fuel_grade",
    "tank_capacity",
    "efficiency",
    "starting_fuel",
    "reserve_fuel",
}


@csrf_exempt
@require_POST
def route_plan_v2(request):
    try:
        payload = _json_body(request)
        route_request = _route_request(payload)
        market = get_market_config()
        catalogue = PricedStationRepository(market).load(
            fuel_type=route_request.vehicle.fuel_type,
            fuel_grade=route_request.vehicle.fuel_grade,
            allow_stale=route_request.allow_stale_prices,
        )
        if catalogue.snapshot_version == "unavailable":
            raise InsufficientPriceDataError(
                f"No active {market.country_name} station snapshot is available."
            )
        plan, cache_status, cache_ttl = get_or_build_route_plan(
            route_request,
            catalogue,
            market,
            builder=lambda: build_route_plan(
                route_request,
                catalogue=catalogue,
                market=market,
            ),
        )
        response = JsonResponse(plan)
        response["X-FuelUp-Cache"] = cache_status
        response["X-FuelUp-Cache-TTL"] = str(cache_ttl)
        return response
    except ApiError as exc:
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
    unexpected = sorted(set(payload) - REQUEST_FIELDS)
    if unexpected:
        raise InvalidRequestError(
            f"Unexpected request fields: {', '.join(unexpected)}."
        )
    return payload


def _route_request(payload):
    vehicle_payload = payload.get("vehicle")
    if not isinstance(vehicle_payload, dict):
        raise InvalidRequestError('"vehicle" must be a JSON object.')
    unexpected = sorted(set(vehicle_payload) - VEHICLE_FIELDS)
    if unexpected:
        raise InvalidRequestError(
            f"Unexpected vehicle fields: {', '.join(unexpected)}."
        )
    try:
        vehicle = VehicleProfile(
            fuel_type=FuelType(vehicle_payload.get("fuel_type")),
            fuel_grade=_optional_string(vehicle_payload, "fuel_grade"),
            tank_capacity=_decimal_field(vehicle_payload, "tank_capacity"),
            efficiency=_decimal_field(vehicle_payload, "efficiency"),
            starting_fuel=_decimal_field(vehicle_payload, "starting_fuel"),
            reserve_fuel=_decimal_field(vehicle_payload, "reserve_fuel"),
        )
        route_request = RoutePlanRequest(
            start=_location(payload, "start"),
            finish=_location(payload, "finish"),
            waypoints=_waypoints(payload),
            vehicle=vehicle,
            maximum_detour=_decimal_field(
                payload,
                "maximum_detour",
                default=Decimal("5"),
            ),
            strategy=RouteStrategy(payload.get("strategy", "balanced")),
            price_quality=PriceQualityPolicy(
                payload.get("price_quality", "best_available")
            ),
            allow_stale_prices=_boolean_field(
                payload, "allow_stale_prices", default=False
            ),
        )
    except (ValueError, TypeError, InvalidOperation) as exc:
        raise InvalidRequestError(str(exc)) from exc
    return route_request


def _location(payload, key):
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise InvalidRequestError(f'"{key}" must be a non-empty string.')
    if len(value) > 300:
        raise InvalidRequestError(f'"{key}" must be 300 characters or fewer.')
    return value.strip()


def _waypoints(payload):
    values = payload.get("waypoints", [])
    if not isinstance(values, list):
        raise InvalidRequestError('"waypoints" must be an array.')
    if len(values) > 5:
        raise InvalidRequestError('"waypoints" supports at most five values.')
    return tuple(_location({"waypoint": value}, "waypoint") for value in values)


def _decimal_field(payload, key, default=None):
    value = payload.get(key, default)
    if value is None or isinstance(value, bool):
        raise InvalidRequestError(f'"{key}" must be a number.')
    try:
        parsed = Decimal(str(value))
    except InvalidOperation as exc:
        raise InvalidRequestError(f'"{key}" must be a number.') from exc
    if not parsed.is_finite():
        raise InvalidRequestError(f'"{key}" must be a finite number.')
    return parsed


def _optional_string(payload, key):
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise InvalidRequestError(f'"{key}" must be a string or null.')
    return value


def _boolean_field(payload, key, default):
    value = payload.get(key, default)
    if not isinstance(value, bool):
        raise InvalidRequestError(f'"{key}" must be a boolean.')
    return value
