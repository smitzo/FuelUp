from django.urls import path

from routes.api.data_status import data_status
from routes.api.station_views import station_detail_v2, station_list_v2
from routes.api.v2_views import route_plan_v2
from routes.api.views import health, readiness, route_plan

urlpatterns = [
    path("v2/data-status/", data_status, name="data-status-v2"),
    path("health/", health, name="health"),
    path("health/live/", health, name="health-live"),
    path("health/ready/", readiness, name="health-ready"),
    path("route/", route_plan, name="route-plan"),
    path("v2/route/", route_plan_v2, name="route-plan-v2"),
    path("v2/stations/", station_list_v2, name="station-list-v2"),
    path(
        "v2/stations/<str:stable_id>/",
        station_detail_v2,
        name="station-detail-v2",
    ),
]
