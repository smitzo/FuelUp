import json
from datetime import datetime, time

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from routes.models import SourceRegistry


class Command(BaseCommand):
    help = "Synchronize the fail-closed external data-source registry."

    def handle(self, *args, **options):
        path = settings.BASE_DIR / "data" / "source-registry.json"
        try:
            registry = json.loads(path.read_text(encoding="utf-8"))
            reviewed_on = datetime.combine(
                datetime.fromisoformat(registry["reviewed_on"]).date(),
                time.min,
                tzinfo=timezone.get_current_timezone(),
            )
            sources = registry["sources"]
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise CommandError("The source registry is invalid.") from exc

        synchronized = 0
        for source in sources:
            SourceRegistry.objects.update_or_create(
                slug=source["slug"],
                defaults={
                    "owner": source["owner"],
                    "purpose": source["purpose"],
                    "terms_url": source["terms_url"],
                    "permission_status": source["permission_status"],
                    "permission_evidence": source["permission_evidence"],
                    "permitted_use": source["permitted_use"],
                    "attribution": source["attribution"],
                    "automated_access_allowed": source[
                        "automated_access_allowed"
                    ],
                    "enabled": source["enabled"],
                    "refresh_budget_per_day": source[
                        "refresh_budget_per_day"
                    ],
                    "retention_policy": source["retention_policy"],
                    "reviewed_at": reviewed_on,
                },
            )
            synchronized += 1

        self.stdout.write(
            self.style.SUCCESS(f"Synchronized {synchronized} data sources.")
        )
