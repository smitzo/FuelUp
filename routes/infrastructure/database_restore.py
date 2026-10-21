"""Prove a fresh PostgreSQL backup in a generated, isolated database."""

import hashlib
import json
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

import psycopg
from psycopg import sql

from routes.infrastructure.database_backup import create_backup, postgres_environment


class RestoreVerificationError(ValueError):
    pass


def connection_parameters(environment):
    parameters = {"connect_timeout": 10, "application_name": "fuelup-restore-drill"}
    for variable, parameter in (
        ("PGDATABASE", "dbname"),
        ("PGUSER", "user"),
        ("PGPASSWORD", "password"),
        ("PGHOST", "host"),
        ("PGPORT", "port"),
        ("PGSSLMODE", "sslmode"),
        ("PGSSLROOTCERT", "sslrootcert"),
        ("PGSSLCERT", "sslcert"),
        ("PGSSLKEY", "sslkey"),
    ):
        if environment.get(variable):
            parameters[parameter] = environment[variable]
    return parameters


def canonical_fingerprint(connection):
    tables = [
        row[0]
        for row in connection.execute(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public' "
            "AND (left(tablename, 7) = 'routes_' OR tablename = 'django_migrations') "
            "ORDER BY tablename"
        )
    ]
    if "routes_priceobservation" not in tables or "django_migrations" not in tables:
        raise RestoreVerificationError("The source database must be fully migrated.")
    contents = {}
    for table in tables:
        digest = hashlib.sha256()
        count = 0
        # Sort serialized rows so physical row order and query plans do not matter.
        # A server-side cursor keeps Python memory bounded for catalogue imports.
        with connection.cursor(name="fuelup_restore_fingerprint") as cursor:
            cursor.execute(
                sql.SQL(
                    "SELECT row_to_json(record)::text FROM {} AS record "
                    'ORDER BY row_to_json(record)::text COLLATE "C"'
                ).format(sql.Identifier("public", table))
            )
            for row in cursor:
                digest.update(row[0].encode("utf-8") + b"\n")
                count += 1
        contents[table] = {"rows": count, "sha256": digest.hexdigest()}
    constraints = list(
        connection.execute(
            "SELECT c.relname, k.conname, pg_get_constraintdef(k.oid) "
            "FROM pg_constraint k JOIN pg_class c ON c.oid = k.conrelid "
            "JOIN pg_namespace n ON n.oid = c.relnamespace "
            "WHERE n.nspname = 'public' AND c.relname = ANY(%s) "
            "ORDER BY c.relname, k.conname",
            (tables,),
        )
    )
    return {"tables": contents, "constraints": constraints}


def verify_database_restore(database):
    environment = postgres_environment(database)
    parameters = connection_parameters(environment)
    # There is deliberately no target-database option: callers cannot select an
    # existing database or accidentally point pg_restore at the source.
    target_name = "fuelup_restore_" + uuid4().hex
    target_created = False
    try:
        with TemporaryDirectory(prefix="fuelup-restore-") as directory:
            backup_path = Path(directory) / "verification.dump"
            with psycopg.connect(**parameters) as source:
                source.execute(
                    "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"
                )
                snapshot = source.execute("SELECT pg_export_snapshot()").fetchone()[0]
                expected = canonical_fingerprint(source)
                backup = create_backup(database, backup_path, snapshot=snapshot)
            maintenance_parameters = {**parameters, "dbname": "postgres"}
            with psycopg.connect(**maintenance_parameters, autocommit=True) as admin:
                try:
                    admin.execute(
                        sql.SQL("CREATE DATABASE {} TEMPLATE template0").format(
                            sql.Identifier(target_name)
                        )
                    )
                    target_created = True
                    subprocess.run(
                        [
                            "pg_restore",
                            "--no-password",
                            "--no-owner",
                            "--no-acl",
                            "--exit-on-error",
                            "--dbname",
                            target_name,
                            str(backup_path),
                        ],
                        env={**environment, "PGDATABASE": target_name},
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.PIPE,
                        check=True,
                    )
                    with psycopg.connect(
                        **{**parameters, "dbname": target_name}
                    ) as target:
                        actual = canonical_fingerprint(target)
                    if actual != expected:
                        raise RestoreVerificationError(
                            "Restored canonical rows or constraints "
                            "do not match the backup."
                        )
                finally:
                    if target_created:
                        try:
                            admin.execute(
                                sql.SQL("DROP DATABASE {}").format(
                                    sql.Identifier(target_name)
                                )
                            )
                        except psycopg.Error:
                            raise RestoreVerificationError(
                                f"Remove the isolated drill database {target_name}; "
                                "automatic cleanup failed."
                            ) from None
            return {
                "status": "passed",
                "snapshot_consistent": True,
                "isolated_database_removed": True,
                "table_count": len(expected["tables"]),
                "row_count": sum(
                    table["rows"] for table in expected["tables"].values()
                ),
                "canonical_sha256": hashlib.sha256(
                    json.dumps(expected, sort_keys=True, separators=(",", ":")).encode(
                        "utf-8"
                    )
                ).hexdigest(),
                "backup": backup,
            }
    except RestoreVerificationError:
        raise
    except (psycopg.Error, OSError, subprocess.CalledProcessError, ValueError):
        raise RestoreVerificationError(
            "Restore verification failed; check PostgreSQL access, matching client "
            "tools, and permission to create an isolated database."
        ) from None
