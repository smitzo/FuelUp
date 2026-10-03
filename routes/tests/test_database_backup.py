from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.test import SimpleTestCase

from routes.infrastructure.database_backup import create_backup, postgres_environment


class DatabaseBackupTests(SimpleTestCase):
    def test_sqlite_is_rejected_and_password_is_only_in_environment(self):
        with self.assertRaises(ValueError):
            postgres_environment({"ENGINE": "django.db.backends.sqlite3"})
        environment = postgres_environment(
            {"ENGINE": "django.db.backends.postgresql", "PASSWORD": "test-password"}
        )
        self.assertEqual(environment["PGPASSWORD"], "test-password")

    @patch("routes.infrastructure.database_backup.subprocess.run")
    def test_backup_is_private_and_never_overwrites(self, run):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "test.dump"
            database = {"ENGINE": "django.db.backends.postgresql"}
            result = create_backup(database, path)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(result["bytes"], 0)
            with self.assertRaises(FileExistsError):
                create_backup(database, path)
            self.assertNotIn("test-password", str(run.call_args.args))
