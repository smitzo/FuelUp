from django.urls import path

from routes.api.v2_views import route_plan_v2
from routes.api.views import health, readiness, route_plan

urlpatterns = [
    path("health/", health, name="health"),
    path("health/live/", health, name="health-live"),
    path("health/ready/", readiness, name="health-ready"),
    path("route/", route_plan, name="route-plan"),
    path("v2/route/", route_plan_v2, name="route-plan-v2"),
]
