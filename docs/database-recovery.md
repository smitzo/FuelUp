# PostgreSQL backup and recovery

Development can use SQLite. Production settings require PostgreSQL. Set a
provider-issued `DATABASE_URL` in backend secret settings; keep SSL options from
that provider. Do not paste passwords into committed files or CLI arguments.

Create a backup on a trusted host with PostgreSQL 18 client tools available:

```bash
mkdir -p backups
.venv/bin/python manage.py backup_database backups/india-before-release.dump
pg_restore --list backups/india-before-release.dump
```

The command reads Django's configured database, creates a mode-0600 file without
overwriting an existing backup, and prints its size and SHA-256. Store a private
copy away from the application host. Set retention and access for contributor
data; do not publish backups as CI artifacts.

## Isolated restore drill

Run against a new disposable local database only. Configure PostgreSQL access
through a protected service file or environment, not a password-bearing command.

```bash
createdb fuelup_restore_drill
PGDATABASE=fuelup_restore_drill pg_restore --no-owner --no-acl --exit-on-error backups/india-before-release.dump
DATABASE_URL=postgresql:///fuelup_restore_drill .venv/bin/python manage.py showmigrations --plan
DATABASE_URL=postgresql:///fuelup_restore_drill .venv/bin/python manage.py check
DATABASE_URL=postgresql:///fuelup_restore_drill .venv/bin/python manage.py provider_status
```

Compare migration state, active station snapshot, station count, observation
count/state, and watermarks with the source backup. Verify constraints and
foreign keys by making a fresh backup of the restored database. Never invoke
`pg_restore --clean` against the running application's database.

Before schema changes, create a backup, review the migration plan, and rehearse
against a copy. On application rollback, retain compatible schema; restoring an
old backup loses subsequent writes and requires a deliberate incident decision.
