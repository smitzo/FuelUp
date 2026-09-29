from django.conf import settings

from routes.domain.exceptions import ExternalServiceError
from routes.infrastructure.mitra_prices import parse_mitra_prices
from routes.infrastructure.provider_http import request_json


class MitraPriceClient:
    source_slug = "api-mitra-fuel"

    def snapshot(self):
        if not settings.API_MITRA_API_KEY:
            raise ExternalServiceError("Price provider key is not configured.")
        payload = request_json(
            self.source_slug,
            settings.API_MITRA_BASE_URL,
            "/fuel",
            headers={"x-api-key": settings.API_MITRA_API_KEY},
        )
        try:
            prices = parse_mitra_prices(payload)
        except (ValueError, TypeError) as exc:
            raise ExternalServiceError(
                "Price snapshot failed freshness or geographic validation."
            ) from exc
        return payload, prices
