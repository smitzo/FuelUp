import json

from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from routes.infrastructure.database_restore import (
    RestoreVerificationError,
    verify_database_restore,
)


class Command(BaseCommand):
    help = (
        "Back up PostgreSQL, restore into a new isolated database, and verify contents."
    )

    def handle(self, *args, **options):
        try:
            report = verify_database_restore(connection.settings_dict)
        except (RestoreVerificationError, ValueError) as exc:
            raise CommandError(str(exc)) from None
        self.stdout.write(json.dumps(report, sort_keys=True))
