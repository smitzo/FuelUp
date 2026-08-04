class ApiError(Exception):
    code = "api_error"
    status = 400

    def __init__(self, message):
        super().__init__(message)
        self.message = message


class RoutePlannerError(ApiError):
    code = "route_planner_error"


class InvalidRequestError(RoutePlannerError):
    code = "invalid_request"


class LocationNotFoundError(RoutePlannerError):
    code = "location_not_found"
    status = 422


class UnsupportedCountryError(RoutePlannerError):
    code = "unsupported_country"
    status = 422


class InsufficientPriceDataError(RoutePlannerError):
    code = "insufficient_price_data"
    status = 422


class RouteNotFoundError(RoutePlannerError):
    code = "route_not_found"
    status = 422


class FuelPlanNotFoundError(RoutePlannerError):
    code = "fuel_plan_not_found"
    status = 422


class ExternalServiceError(RoutePlannerError):
    code = "external_service_error"
    status = 502


class StationCatalogueUnavailableError(ApiError):
    code = "station_catalogue_unavailable"
    status = 503


class StationNotFoundError(ApiError):
    code = "station_not_found"
    status = 404


class ContributionUnavailableError(ApiError):
    code = "contribution_unavailable"
    status = 503


class ContributionRateLimitError(ApiError):
    code = "contribution_rate_limited"
    status = 429

    def __init__(self, message, *, retry_after):
        super().__init__(message)
        self.retry_after = retry_after


class ContributionConflictError(ApiError):
    code = "contribution_conflict"
    status = 409


class ContributionReceiptNotFoundError(ApiError):
    code = "contribution_receipt_not_found"
    status = 404
