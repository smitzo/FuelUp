from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from routes.application.price_import import import_provider_prices
from routes.domain.exceptions import ApiError
from routes.infrastructure.mitra_client import MitraPriceClient
from routes.models import PriceImportBatch, SourceRegistry


class Command(BaseCommand):
    help = "Refresh approved India prices once daily; safe for repeated scheduler runs."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Ignore cadence; all provider request budgets still apply.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        source = (
            SourceRegistry.objects.select_for_update()
            .filter(slug=MitraPriceClient.source_slug)
            .first()
        )
        if not source or not source.can_fetch or not source._has_approved_terms:
            raise CommandError(
                "API Mitra is disabled or awaiting its recorded terms review."
            )
        if source.purpose != "third_party_price_reference":
            raise CommandError(
                "The configured source is not a third-party price source."
            )
        latest = (
            PriceImportBatch.objects.filter(source=source)
            .order_by("-imported_at")
            .first()
        )
        if (
            not options["force"]
            and latest
            and latest.imported_at > timezone.now() - timedelta(hours=24)
        ):
            self.stdout.write(
                "Skipped: a snapshot was imported within the last 24 hours."
            )
            return
        try:
            _, prices = MitraPriceClient().snapshot()
            batch, created = import_provider_prices(source.slug, prices)
        except (ApiError, ValueError) as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(
            f"Batch {batch.pk}: {'imported' if created else 'unchanged'}; "
            f"{batch.accepted_count} accepted, {batch.quarantined_count} quarantined, "
            f"{batch.rejected_count} rejected."
        )
