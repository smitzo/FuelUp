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

The automated drill creates a backup from one exported, read-only PostgreSQL
snapshot and restores it into a randomly named `fuelup_restore_...` database:

```bash
.venv/bin/python manage.py verify_database_restore
```

Use a trusted maintenance host with matching PostgreSQL client tools and a
database role allowed to create disposable databases. The command never accepts
an existing restore target. It compares every `routes_` table, migration history,
and database constraints, then removes its temporary backup and database on both
success and restore failure. If database cleanup fails, the command reports the
generated database name for manual removal; it never reports success.

The JSON report contains only counts and hashes, without rows, credentials,
contributor identifiers, or locations. Concurrent writes after snapshot export
are excluded consistently from both the fingerprint and backup. Run the drill
weekly and before a pilot release; retain the redacted report with its release
revision. This verifies a new logical backup; rehearse older retained backups
separately to verify off-host retention and disaster recovery. It does not
restore roles/ownership, a deployment artifact, or provider credentials.

The PostgreSQL integration suite exercises a synthetic catalogue, observations,
moderation event, contribution receipt, watermark, concurrent source write, and
an injected `pg_restore` failure. Fixtures are never public product data.

### Rehearse a retained backup manually

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
