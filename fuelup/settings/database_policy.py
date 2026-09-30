from django.core.exceptions import ImproperlyConfigured


def require_durable_database(database):
    if database.get("ENGINE") != "django.db.backends.postgresql":
        raise ImproperlyConfigured(
            "Production requires a PostgreSQL DATABASE_URL. "
            "SQLite remains available with development settings."
        )
