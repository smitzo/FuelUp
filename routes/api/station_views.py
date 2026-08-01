from django.http import JsonResponse
from django.views.decorators.http import require_GET

from routes.application.market import get_market_config
from routes.application.station_directory import (
    get_station_detail,
    search_station_directory,
)
from routes.domain.exceptions import ApiError, InvalidRequestError
from routes.domain.fuel_data import FuelType

LIST_QUERY_FIELDS = {"q", "fuel_type", "fuel_grade", "page", "page_size"}


@require_GET
def station_list_v2(request):
    try:
        values = _validated_query(request.GET)
        return JsonResponse(
            search_station_directory(
                get_market_config(),
                query=values["query"],
                fuel_type=values["fuel_type"],
                fuel_grade=values["fuel_grade"],
                page=values["page"],
                page_size=values["page_size"],
            )
        )
    except ApiError as exc:
        return _error_response(exc)


@require_GET
def station_detail_v2(request, stable_id):
    try:
        station_id = _bounded_text(stable_id, "station_id", maximum=120)
        return JsonResponse(get_station_detail(get_market_config(), station_id))
    except ApiError as exc:
        return _error_response(exc)


def _validated_query(query):
    unexpected = sorted(set(query) - LIST_QUERY_FIELDS)
    if unexpected:
        raise InvalidRequestError(f"Unexpected query fields: {', '.join(unexpected)}.")
    repeated = sorted(key for key, values in query.lists() if len(values) != 1)
    if repeated:
        raise InvalidRequestError(
            f"Query fields may appear only once: {', '.join(repeated)}."
        )
    fuel_value = query.get("fuel_type")
    try:
        fuel_type = FuelType(fuel_value) if fuel_value else None
    except ValueError as exc:
        raise InvalidRequestError('"fuel_type" must be petrol or diesel.') from exc
    fuel_grade = query.get("fuel_grade")
    if fuel_grade is not None:
        fuel_grade = _bounded_text(fuel_grade, "fuel_grade", maximum=50)
    return {
        "query": _optional_bounded_text(query.get("q"), "q", maximum=100),
        "fuel_type": fuel_type,
        "fuel_grade": fuel_grade,
        "page": _positive_integer(query.get("page"), "page", default=1),
        "page_size": _positive_integer(
            query.get("page_size"),
            "page_size",
            default=20,
            maximum=50,
        ),
    }


def _positive_integer(value, field, *, default, maximum=10_000):
    if value is None:
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise InvalidRequestError(f'"{field}" must be an integer.') from exc
    if str(parsed) != value or not 1 <= parsed <= maximum:
        raise InvalidRequestError(f'"{field}" must be between 1 and {maximum}.')
    return parsed


def _optional_bounded_text(value, field, *, maximum):
    if value is None or value == "":
        return ""
    return _bounded_text(value, field, maximum=maximum)


def _bounded_text(value, field, *, maximum):
    if (
        not isinstance(value, str)
        or not value.strip()
        or len(value.strip()) > maximum
        or not value.isprintable()
    ):
        raise InvalidRequestError(
            f'"{field}" must contain 1 to {maximum} printable characters.'
        )
    return value.strip()


def _error_response(error):
    return JsonResponse(
        {"error": {"code": error.code, "message": error.message}},
        status=error.status,
    )
