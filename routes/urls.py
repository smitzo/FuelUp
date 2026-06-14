from django.urls import path

from routes.api.views import health, route_plan

urlpatterns = [
    path("health/", health, name="health"),
    path("route/", route_plan, name="route-plan"),
]
