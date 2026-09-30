import json

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from routes.domain.entities import Coordinate, GeocodedLocation
from routes.domain.exceptions import ApiError
from routes.infrastructure.heigit_client import HeiGitRoutingClient
from routes.infrastructure.mitra_client import MitraPriceClient
from routes.models import ProviderHealth, SourceRegistry


class Command(BaseCommand):
    help = "Show redacted provider configuration. Network checks are explicitly opt-in."

    def add_arguments(self, parser):
        parser.add_argument("--check-live", choices=("routing", "prices"))

    def handle(self, *args, **options):
        rows = []
        for slug, present in (
            ("api-mitra-fuel", bool(settings.API_MITRA_API_KEY)),
            ("heigit-openrouteservice", bool(settings.HEIGIT_API_KEY)),
        ):
            source = SourceRegistry.objects.filter(slug=slug).first()
            health = ProviderHealth.objects.filter(source_id=slug).first()
            rows.append(
                {
                    "provider": slug,
                    "key_configured": present,
                    "enabled": bool(source and source.can_fetch),
                    "monthly_limit": settings.PROVIDER_MONTHLY_LIMITS.get(slug, 0),
                    "last_success_at": health.last_success_at if health else None,
                    "last_error_code": health.last_error_code if health else "",
                }
            )
        self.stdout.write(json.dumps(rows, default=str))
        try:
            if options["check_live"] == "prices":
                _, prices = MitraPriceClient().snapshot()
                self.stdout.write(
                    f"Validated {len(prices)} reference observations; not imported."
                )
            elif options["check_live"] == "routing":
                locations = [
                    GeocodedLocation(name, name, Coordinate(lat, lon))
                    for name, lat, lon in (
                        ("Ahmedabad", 23.0225, 72.5714),
                        ("Vadodara", 22.3072, 73.1812),
                    )
                ]
                routes = HeiGitRoutingClient().routes_through(locations)
                self.stdout.write(f"Validated {len(routes)} India route alternatives.")
        except (ApiError, SourceRegistry.DoesNotExist) as exc:
            raise CommandError(
                "Provider check failed; inspect configuration and recorded health."
            ) from exc
