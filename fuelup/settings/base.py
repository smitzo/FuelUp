import os
from pathlib import Path

import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent.parent


def env_bool(name, default=False):
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def env_int(name, default):
    return int(os.getenv(name, str(default)))


def env_float(name, default):
    return float(os.getenv(name, str(default)))


def env_list(name, default=""):
    return [
        value.strip()
        for value in os.getenv(name, default).split(",")
        if value.strip()
    ]


SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "development-only-secret-key")
DEBUG = False
ALLOWED_HOSTS = env_list(
    "DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,testserver"
)

INSTALLED_APPS = [
    "django.contrib.staticfiles",
    "routes",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "fuelup.urls"
TEMPLATES = []
WSGI_APPLICATION = "fuelup.wsgi.application"
ASGI_APPLICATION = "fuelup.asgi.application"

DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=env_int("DATABASE_CONN_MAX_AGE", 60),
        conn_health_checks=True,
    )
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    }
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

ROUTING_BASE_URL = os.getenv("ROUTING_BASE_URL", "https://router.project-osrm.org")
GEOCODING_BASE_URL = os.getenv(
    "GEOCODING_BASE_URL", "https://nominatim.openstreetmap.org"
)
EXTERNAL_API_USER_AGENT = os.getenv(
    "EXTERNAL_API_USER_AGENT",
    "FuelUpRouteExercise/1.0 (contact: joshismit2812@gmail.com)",
)
EXTERNAL_API_TIMEOUT_SECONDS = env_float("EXTERNAL_API_TIMEOUT_SECONDS", 8)
GEOCODE_CACHE_SECONDS = env_int("GEOCODE_CACHE_SECONDS", 86_400)
ROUTE_CACHE_SECONDS = env_int("ROUTE_CACHE_SECONDS", 3_600)
ROUTE_ALTERNATIVES = env_int("ROUTE_ALTERNATIVES", 3)
ROUTE_TIME_VALUE_USD_PER_HOUR = env_float(
    "ROUTE_TIME_VALUE_USD_PER_HOUR", 8
)
ROUTE_STOP_PENALTY_USD = env_float("ROUTE_STOP_PENALTY_USD", 4)

REDIS_URL = os.getenv("REDIS_URL")
if REDIS_URL:
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": REDIS_URL,
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
                "IGNORE_EXCEPTIONS": True,
                "SOCKET_CONNECT_TIMEOUT": 2,
                "SOCKET_TIMEOUT": 2,
            },
            "TIMEOUT": GEOCODE_CACHE_SECONDS,
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.filebased.FileBasedCache",
            "LOCATION": os.getenv("CACHE_DIR", "/tmp/fuelup-cache"),
            "TIMEOUT": GEOCODE_CACHE_SECONDS,
            "OPTIONS": {"MAX_ENTRIES": 2_000},
        }
    }

SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
