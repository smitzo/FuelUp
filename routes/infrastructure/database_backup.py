import hashlib
import os
import subprocess
from pathlib import Path


def postgres_environment(database):
    if database["ENGINE"] != "django.db.backends.postgresql":
        raise ValueError("Database backups require PostgreSQL.")
    environment = os.environ.copy()
    for setting, variable in (
        ("NAME", "PGDATABASE"),
        ("USER", "PGUSER"),
        ("PASSWORD", "PGPASSWORD"),
        ("HOST", "PGHOST"),
        ("PORT", "PGPORT"),
    ):
        environment[variable] = str(database.get(setting) or "")
    for option in ("sslmode", "sslrootcert", "sslcert", "sslkey"):
        if option in database.get("OPTIONS", {}):
            environment["PG" + option.upper()] = str(database["OPTIONS"][option])
    return environment


def create_backup(database, output_path):
    environment = postgres_environment(database)
    path = Path(output_path)
    # Exclusive creation protects existing backups; private mode protects contents.
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as output:
            subprocess.run(
                [
                    "pg_dump",
                    "--no-password",
                    "--format=custom",
                    "--no-owner",
                    "--no-acl",
                ],
                stdout=output,
                stderr=subprocess.PIPE,
                env=environment,
                check=True,
            )
    except (OSError, subprocess.CalledProcessError) as exc:
        path.unlink(missing_ok=True)
        raise ValueError(
            "PostgreSQL backup failed; no partial backup was retained."
        ) from exc
    with path.open("rb") as backup:
        digest = hashlib.file_digest(backup, "sha256").hexdigest()
    return {"sha256": digest, "bytes": path.stat().st_size}
