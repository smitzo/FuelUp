import json

from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from routes.infrastructure.database_backup import create_backup


class Command(BaseCommand):
    help = "Create a private, non-overwriting PostgreSQL custom-format backup."

    def add_arguments(self, parser):
        parser.add_argument("output_path")

    def handle(self, *args, **options):
        try:
            metadata = create_backup(connection.settings_dict, options["output_path"])
        except (OSError, ValueError) as exc:
            raise CommandError(
                "Backup failed; check PostgreSQL access and output path."
            ) from exc
        self.stdout.write(json.dumps(metadata))
