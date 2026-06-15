from django.urls import path

from routes.api.views import health, readiness, route_plan

urlpatterns = [
    path("health/", health, name="health"),
    path("health/live/", health, name="health-live"),
    path("health/ready/", readiness, name="health-ready"),
    path("route/", route_plan, name="route-plan"),
]
