from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase

from routes.tests.database_fixture import seed_recovery_fixture


class ProviderMigrationTests(TransactionTestCase):
    """Run on both CI databases; never touch the configured application database."""

    old = ("routes", "0003_contributionreceipt_payload_hash")
    new = ("routes", "0005_provider_usage_and_health")
    canonical_models = (
        "SourceRegistry",
        "StationSnapshot",
        "FuelStation",
        "StationFuel",
        "PriceImportBatch",
        "PriceObservation",
        "PriceModerationEvent",
        "ContributionReceipt",
        "ObservationWatermark",
    )

    def migrate_to(self, target):
        executor = MigrationExecutor(connection)
        executor.migrate([target])
        return executor.loader.project_state([target]).apps

    def contents(self, apps):
        return {
            name: list(apps.get_model("routes", name).objects.order_by("pk").values())
            for name in self.canonical_models
        }

    def test_forward_backward_forward_preserves_canonical_rows(self):
        try:
            old_apps = self.migrate_to(self.old)
            seed_recovery_fixture(old_apps)
            expected = self.contents(old_apps)
            new_apps = self.migrate_to(self.new)
            self.assertEqual(self.contents(new_apps), expected)
            source = new_apps.get_model("routes", "SourceRegistry").objects.get()
            new_apps.get_model("routes", "ProviderHealth").objects.create(source=source)
            self.assertEqual(self.contents(self.migrate_to(self.old)), expected)
            self.assertEqual(self.contents(self.migrate_to(self.new)), expected)
            self.assertFalse(
                new_apps.get_model("routes", "ProviderHealth").objects.exists()
            )
        finally:
            # Restore the full schema even when an assertion fails.
            executor = MigrationExecutor(connection)
            executor.migrate(executor.loader.graph.leaf_nodes())
