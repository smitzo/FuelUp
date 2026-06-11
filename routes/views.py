from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST


@require_GET
def health(request):
    return JsonResponse({"status": "ok"})


@require_POST
def route_plan(request):
    return JsonResponse(
        {"error": {"code": "not_implemented", "message": "Route API is not ready."}},
        status=501,
    )
