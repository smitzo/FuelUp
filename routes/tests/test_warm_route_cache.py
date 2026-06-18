from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase

from routes.management.commands.warm_route_cache import DEFAULT_ROUTES


class WarmRouteCacheCommandTests(SimpleTestCase):
    @patch(
        "routes.management.commands.warm_route_cache.get_or_build_route_plan",
        return_value=({"route": {}}, "MISS"),
    )
    def test_warms_default_frontend_routes(self, get_or_build):
        output = StringIO()

        call_command("warm_route_cache", stdout=output)

        self.assertEqual(get_or_build.call_count, len(DEFAULT_ROUTES))
        self.assertIn("Los Angeles, CA -> New York, NY", output.getvalue())

    @patch(
        "routes.management.commands.warm_route_cache.get_or_build_route_plan",
        side_effect=RuntimeError("provider unavailable"),
    )
    def test_best_effort_does_not_block_startup(self, get_or_build):
        errors = StringIO()

        call_command(
            "warm_route_cache",
            "--best-effort",
            "--route",
            "Austin, TX",
            "Denver, CO",
            stderr=errors,
        )

        self.assertIn("provider unavailable", errors.getvalue())
        get_or_build.assert_called_once()

    @patch(
        "routes.management.commands.warm_route_cache.get_or_build_route_plan",
        side_effect=RuntimeError("provider unavailable"),
    )
    def test_failure_is_nonzero_without_best_effort(self, get_or_build):
        with self.assertRaises(CommandError):
            call_command(
                "warm_route_cache",
                "--route",
                "Austin, TX",
                "Denver, CO",
            )

        get_or_build.assert_called_once()
