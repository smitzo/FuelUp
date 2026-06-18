from time import perf_counter

from django.core.management.base import BaseCommand, CommandError

from routes.application.plan_cache import get_or_build_route_plan
from routes.application.planner import build_route_plan

DEFAULT_ROUTES = (
    ("Los Angeles, CA", "New York, NY"),
    ("Austin, TX", "Denver, CO"),
    ("Seattle, WA", "Miami, FL"),
)


class Command(BaseCommand):
    help = "Precompute frequently requested routes in the shared cache."

    def add_arguments(self, parser):
        parser.add_argument(
            "--route",
            action="append",
            nargs=2,
            metavar=("START", "FINISH"),
            help="Warm a route instead of the default frontend presets.",
        )
        parser.add_argument(
            "--best-effort",
            action="store_true",
            help="Log failures and continue so application startup can proceed.",
        )

    def handle(self, *args, **options):
        routes = options["route"] or DEFAULT_ROUTES
        failures = []

        for start, finish in routes:
            started = perf_counter()
            try:
                _, cache_status = get_or_build_route_plan(
                    start,
                    finish,
                    builder=build_route_plan,
                )
            except Exception as exc:
                failures.append(f"{start} -> {finish}: {exc}")
                self.stderr.write(
                    self.style.WARNING(
                        f"Failed {start} -> {finish}: {exc}"
                    )
                )
                continue

            elapsed = perf_counter() - started
            self.stdout.write(
                self.style.SUCCESS(
                    f"{cache_status} {start} -> {finish} ({elapsed:.2f}s)"
                )
            )

        if failures and not options["best_effort"]:
            raise CommandError(
                f"Failed to warm {len(failures)} route(s): "
                + "; ".join(failures)
            )
