from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

from fuelup.settings.database_policy import require_durable_database


class DatabasePolicyTests(SimpleTestCase):
    def test_production_rejects_ephemeral_sqlite(self):
        with self.assertRaisesMessage(ImproperlyConfigured, "PostgreSQL"):
            require_durable_database({"ENGINE": "django.db.backends.sqlite3"})
        require_durable_database({"ENGINE": "django.db.backends.postgresql"})
