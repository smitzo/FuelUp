import shutil
import subprocess
from io import StringIO
from unittest import skipUnless
from unittest.mock import patch

import psycopg
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.test import SimpleTestCase, TransactionTestCase

from routes.infrastructure.database_backup import create_backup, postgres_environment
from routes.infrastructure.database_restore import (
    RestoreVerificationError,
    canonical_fingerprint,
    connection_parameters,
    verify_database_restore,
)
from routes.models import SourceRegistry
from routes.tests.database_fixture import seed_recovery_fixture


class RestoreCommandTests(SimpleTestCase):
    @patch("routes.management.commands.verify_database_restore.verify_database_restore")
    def test_command_reports_only_sanitized_failure(self, verify):
        verify.side_effect = RestoreVerificationError("Isolated verification failed.")
        with self.assertRaisesMessage(CommandError, "Isolated verification failed"):
            call_command("verify_database_restore", stdout=StringIO())

    def test_sqlite_is_rejected_before_any_database_is_created(self):
        with self.assertRaisesMessage(ValueError, "PostgreSQL"):
            verify_database_restore({"ENGINE": "django.db.backends.sqlite3"})


@skipUnless(
    connection.vendor == "postgresql"
    and shutil.which("pg_dump")
    and shutil.which("pg_restore"),
    "The isolated restore drill requires PostgreSQL and its client tools.",
)
class PostgreSQLRestoreTests(TransactionTestCase):
    def setUp(self):
        seed_recovery_fixture()
        self.database = connection.settings_dict
        self.parameters = connection_parameters(postgres_environment(self.database))

    def fingerprint(self):
        with psycopg.connect(**self.parameters) as source:
            return canonical_fingerprint(source)

    def drill_databases(self):
        with psycopg.connect(**self.parameters) as source:
            return set(
                source.execute(
                    "SELECT datname FROM pg_database "
                    "WHERE left(datname, 15) = 'fuelup_restore_'"
                )
            )

    def test_restore_preserves_canonical_rows_and_removes_isolated_database(self):
        expected = self.fingerprint()
        existing_drills = self.drill_databases()
        report = verify_database_restore(self.database)
        self.assertEqual(report["status"], "passed")
        self.assertTrue(report["isolated_database_removed"])
        self.assertTrue(report["snapshot_consistent"])
        self.assertGreater(report["backup"]["bytes"], 0)
        self.assertEqual(len(report["canonical_sha256"]), 64)
        self.assertEqual(self.fingerprint(), expected)
        self.assertEqual(self.drill_databases(), existing_drills)

    def test_concurrent_write_does_not_change_exported_backup_snapshot(self):
        def backup_with_concurrent_write(*args, **kwargs):
            SourceRegistry.objects.create(
                slug="synthetic-concurrent-write",
                owner="Synthetic tests",
                purpose="recovery_test",
                terms_url="https://example.invalid/terms",
                permitted_use="Synthetic tests only.",
            )
            return create_backup(*args, **kwargs)

        with patch(
            "routes.infrastructure.database_restore.create_backup",
            side_effect=backup_with_concurrent_write,
        ):
            report = verify_database_restore(self.database)
        self.assertEqual(report["status"], "passed")
        self.assertTrue(
            SourceRegistry.objects.filter(slug="synthetic-concurrent-write").exists()
        )

    def test_restore_failure_cleans_up_and_never_alters_source(self):
        expected = self.fingerprint()
        existing_drills = self.drill_databases()
        run = subprocess.run

        def fail_only_restore(command, **kwargs):
            if command[0] == "pg_restore":
                raise subprocess.CalledProcessError(1, command, stderr=b"private data")
            return run(command, **kwargs)

        with patch(
            "routes.infrastructure.database_restore.subprocess.run",
            side_effect=fail_only_restore,
        ):
            with self.assertRaisesMessage(
                RestoreVerificationError, "Restore verification failed"
            ):
                verify_database_restore(self.database)
        self.assertEqual(self.fingerprint(), expected)
        self.assertEqual(self.drill_databases(), existing_drills)

    def test_altered_restored_price_fails_integrity_check_and_cleans_up(self):
        expected = self.fingerprint()
        existing_drills = self.drill_databases()
        run = subprocess.run

        def corrupt_only_restored_data(command, **kwargs):
            result = run(command, **kwargs)
            if command[0] == "pg_restore":
                target_name = command[command.index("--dbname") + 1]
                self.assertTrue(target_name.startswith("fuelup_restore_"))
                self.assertNotEqual(target_name, self.database["NAME"])
                with psycopg.connect(
                    **{**self.parameters, "dbname": target_name}
                ) as db:
                    db.execute(
                        "UPDATE routes_priceobservation SET unit_price = unit_price + 1"
                    )
            return result

        with patch(
            "routes.infrastructure.database_restore.subprocess.run",
            side_effect=corrupt_only_restored_data,
        ):
            with self.assertRaisesMessage(RestoreVerificationError, "do not match"):
                verify_database_restore(self.database)
        self.assertEqual(self.fingerprint(), expected)
        self.assertEqual(self.drill_databases(), existing_drills)
