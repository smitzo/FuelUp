import json

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count, Q

from routes.models import FuelStation, StationFuel, StationSnapshot


class Command(BaseCommand):
    help = "Measure active India catalogue quality without calling external providers."

    def handle(self, *args, **options):
        snapshot = StationSnapshot.objects.filter(
            market_code="IN", is_active=True, is_valid=True
        ).first()
        if snapshot is None:
            raise CommandError("No active India station snapshot is available.")
        stations = FuelStation.objects.filter(snapshot=snapshot)
        total = stations.count()
        duplicate_coordinates = (
            stations.values("latitude", "longitude")
            .annotate(count=Count("pk"))
            .filter(count__gt=1)
            .count()
        )
        fuels = list(
            StationFuel.objects.filter(station__snapshot=snapshot)
            .values("fuel_type", "is_inferred")
            .annotate(stations=Count("station", distinct=True))
        )
        self.stdout.write(
            json.dumps(
                {
                    "snapshot": snapshot.version,
                    "generated_at": snapshot.source_generated_at,
                    "stations": total,
                    "missing_city": stations.filter(city="").count(),
                    "missing_state": stations.filter(state="").count(),
                    "missing_address": stations.filter(address="").count(),
                    "unnamed": stations.filter(
                        Q(name="") | Q(name="Unnamed fuel station")
                    ).count(),
                    "duplicate_coordinate_groups": duplicate_coordinates,
                    "declared_and_inferred_fuels": fuels,
                    "warning": (
                        "Catalogue completeness does not establish "
                        "current pump prices or stock."
                    ),
                },
                default=str,
            )
        )
