import os
from decimal import Decimal
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
# Deployment environment always takes precedence over the local ignored file.
load_dotenv(BASE_DIR / ".env", override=False)


def env_bool(name, default=False):
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def env_int(name, default):
    return int(os.getenv(name, str(default)))


def env_float(name, default):
    return float(os.getenv(name, str(default)))


def env_decimal(name, default):
    return Decimal(os.getenv(name, str(default)))


def env_list(name, default=""):
    return [
        value.strip() for value in os.getenv(name, default).split(",") if value.strip()
    ]


SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "development-only-secret-key")
DEBUG = False
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,testserver")

INSTALLED_APPS = [
    "django.contrib.staticfiles",
    "routes",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "routes.api.request_context.RequestContextMiddleware",
    "routes.api.rate_limit.RouteRateLimitMiddleware",
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

LANGUAGE_CODE = os.getenv("APP_LANGUAGE_CODE", "en-in")
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
DATA_UPLOAD_MAX_MEMORY_SIZE = 16_384

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

ROUTING_BASE_URL = os.getenv("ROUTING_BASE_URL", "https://router.project-osrm.org")
GEOCODING_BASE_URL = os.getenv(
    "GEOCODING_BASE_URL", "https://nominatim.openstreetmap.org"
)
EXTERNAL_API_USER_AGENT = os.getenv(
    "EXTERNAL_API_USER_AGENT",
    "FuelUp/2.0 (development; configure EXTERNAL_API_USER_AGENT)",
)
API_MITRA_API_KEY = os.getenv("API_MITRA_API_KEY", "")
HEIGIT_API_KEY = os.getenv("HEIGIT_API_KEY", "")
API_MITRA_BASE_URL = os.getenv("API_MITRA_BASE_URL", "https://api.apimitra.in")
HEIGIT_BASE_URL = os.getenv("HEIGIT_BASE_URL", "https://api.openrouteservice.org")
PRICE_SOURCE_SLUG = os.getenv("PRICE_SOURCE_SLUG", "api-mitra-fuel")
PROVIDER_MAX_RESPONSE_BYTES = env_int("PROVIDER_MAX_RESPONSE_BYTES", 2_000_000)
PROVIDER_MONTHLY_LIMITS = {
    "api-mitra-fuel": env_int("API_MITRA_MONTHLY_LIMIT", 0),
    "heigit-openrouteservice": env_int("HEIGIT_MONTHLY_LIMIT", 1500),
}
PROVIDER_DAILY_LIMITS = {
    "api-mitra-fuel": env_int("API_MITRA_DAILY_LIMIT", 2),
    "heigit-openrouteservice": env_int("HEIGIT_DAILY_LIMIT", 100),
}
PROVIDER_MINUTE_LIMITS = {
    "api-mitra-fuel": env_int("API_MITRA_MINUTE_LIMIT", 2),
    "heigit-openrouteservice": env_int("HEIGIT_MINUTE_LIMIT", 30),
}
PROVIDER_CIRCUIT_FAILURES = env_int("PROVIDER_CIRCUIT_FAILURES", 3)
PROVIDER_CIRCUIT_SECONDS = env_int("PROVIDER_CIRCUIT_SECONDS", 120)
EXTERNAL_API_TIMEOUT_SECONDS = env_float("EXTERNAL_API_TIMEOUT_SECONDS", 8)
GEOCODE_CACHE_SECONDS = env_int("GEOCODE_CACHE_SECONDS", 86_400)
ROUTE_CACHE_SECONDS = env_int("ROUTE_CACHE_SECONDS", 2_592_000)
ROUTE_CACHE_LOCK_WAIT_SECONDS = env_float("ROUTE_CACHE_LOCK_WAIT_SECONDS", 15)
ROUTE_ALTERNATIVES = env_int("ROUTE_ALTERNATIVES", 3)
ROUTE_GEOMETRY_OVERVIEW = os.getenv("ROUTE_GEOMETRY_OVERVIEW", "simplified")
ROUTE_TIME_VALUE_USD_PER_HOUR = env_float("ROUTE_TIME_VALUE_USD_PER_HOUR", 8)
ROUTE_STOP_PENALTY_USD = env_float("ROUTE_STOP_PENALTY_USD", 4)
MARKET_CONFIG = {
    "code": os.getenv("MARKET_CODE", "IN"),
    "country_code": os.getenv("MARKET_COUNTRY_CODE", "in"),
    "country_name": os.getenv("MARKET_COUNTRY_NAME", "India"),
    "country_geography_id": os.getenv("MARKET_COUNTRY_GEOGRAPHY_ID", "india"),
    "currency_code": os.getenv("MARKET_CURRENCY_CODE", "INR"),
    "distance_unit": os.getenv("MARKET_DISTANCE_UNIT", "km"),
    "volume_unit": os.getenv("MARKET_VOLUME_UNIT", "litre"),
    "efficiency_unit": os.getenv("MARKET_EFFICIENCY_UNIT", "km/litre"),
    "distance_units_per_mile": env_float("MARKET_DISTANCE_UNITS_PER_MILE", 1.609344),
    "time_value_per_hour": env_float("PLAN_TIME_VALUE_PER_HOUR", 300),
    "stop_penalty": env_float("PLAN_STOP_PENALTY", 150),
    "route_cache_seconds": env_int("PLAN_CACHE_SECONDS", 3600),
    "station_source_slug": os.getenv("STATION_SOURCE_SLUG", "geofabrik-india-osm"),
    "geocoding_source_slug": os.getenv("GEOCODING_SOURCE_SLUG", "osm-public-nominatim"),
    "routing_source_slug": os.getenv("ROUTING_SOURCE_SLUG", "project-osrm-public-demo"),
}
OBSERVATION_POLICY = {
    "min_unit_price": env_decimal("OBSERVATION_MIN_UNIT_PRICE", "20"),
    "max_unit_price": env_decimal("OBSERVATION_MAX_UNIT_PRICE", "300"),
    "max_age_seconds": env_int("OBSERVATION_MAX_AGE_SECONDS", 172_800),
    "future_skew_seconds": env_int("OBSERVATION_FUTURE_SKEW_SECONDS", 300),
    "duplicate_window_seconds": env_int("OBSERVATION_DUPLICATE_WINDOW_SECONDS", 1_800),
    "rapid_update_window_seconds": env_int(
        "OBSERVATION_RAPID_UPDATE_WINDOW_SECONDS", 600
    ),
    "absolute_outlier_tolerance": env_decimal(
        "OBSERVATION_ABSOLUTE_OUTLIER_TOLERANCE", "5"
    ),
    "relative_outlier_tolerance": env_decimal(
        "OBSERVATION_RELATIVE_OUTLIER_TOLERANCE", "0.10"
    ),
    "community_freshness_seconds": env_int("COMMUNITY_PRICE_FRESHNESS_SECONDS", 86_400),
    "reference_freshness_seconds": env_int(
        "REFERENCE_PRICE_FRESHNESS_SECONDS", 129_600
    ),
}
CONTRIBUTION_HASH_SECRET = os.getenv("CONTRIBUTION_HASH_SECRET", SECRET_KEY)
COMMUNITY_SOURCE_SLUG = os.getenv("COMMUNITY_SOURCE_SLUG", "fuelup-community")
CONTRIBUTION_RECEIPT_TTL_SECONDS = env_int(
    "CONTRIBUTION_RECEIPT_TTL_SECONDS", 2_592_000
)
CONTRIBUTION_MAX_BODY_BYTES = env_int("CONTRIBUTION_MAX_BODY_BYTES", 8_192)
CONTRIBUTION_RATE_LIMIT_WINDOW_SECONDS = env_int(
    "CONTRIBUTION_RATE_LIMIT_WINDOW_SECONDS", 3_600
)
CONTRIBUTION_RATE_LIMITS = {
    "network": env_int("CONTRIBUTION_NETWORK_LIMIT", 60),
    "device": env_int("CONTRIBUTION_DEVICE_LIMIT", 30),
    "contributor": env_int("CONTRIBUTION_CONTRIBUTOR_LIMIT", 20),
    "station": env_int("CONTRIBUTION_STATION_LIMIT", 100),
}
ROUTE_RATE_LIMIT_REQUESTS = env_int("ROUTE_RATE_LIMIT_REQUESTS", 30)
ROUTE_RATE_LIMIT_WINDOW_SECONDS = env_int("ROUTE_RATE_LIMIT_WINDOW_SECONDS", 60)
TRUST_PROXY_HEADERS = env_bool("TRUST_PROXY_HEADERS", False)
RELEASE_SHA = os.getenv(
    "RELEASE_SHA",
    os.getenv("RENDER_GIT_COMMIT", "development"),
)

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

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {"()": "fuelup.logging.JsonFormatter"},
        "console": {"format": "%(levelname)s %(name)s %(message)s"},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "console",
        },
        "json": {
            "class": "logging.StreamHandler",
            "formatter": "json",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": LOG_LEVEL,
    },
    "loggers": {
        "fuelup": {
            "handlers": ["console"],
            "level": LOG_LEVEL,
            "propagate": False,
        }
    },
}
