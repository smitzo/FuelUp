class RoutePlannerError(Exception):
    code = "route_planner_error"
    status = 400

    def __init__(self, message):
        super().__init__(message)
        self.message = message


class InvalidRequestError(RoutePlannerError):
    code = "invalid_request"


class LocationNotFoundError(RoutePlannerError):
    code = "location_not_found"
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

