import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "development-only-secret-key")
DEBUG = os.getenv("DJANGO_DEBUG", "false").lower() == "true"
ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,testserver").split(",")
    if host.strip()
]

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
    "routes",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "fuelup.urls"
TEMPLATES = []
WSGI_APPLICATION = "fuelup.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

ROUTING_BASE_URL = os.getenv("ROUTING_BASE_URL", "https://router.project-osrm.org")
GEOCODING_BASE_URL = os.getenv(
    "GEOCODING_BASE_URL", "https://nominatim.openstreetmap.org"
)
EXTERNAL_API_USER_AGENT = os.getenv(
    "EXTERNAL_API_USER_AGENT",
    "FuelUpRouteExercise/1.0 (configure-contact@example.com)",
)
EXTERNAL_API_TIMEOUT_SECONDS = float(os.getenv("EXTERNAL_API_TIMEOUT_SECONDS", "8"))
GEOCODE_CACHE_SECONDS = int(os.getenv("GEOCODE_CACHE_SECONDS", "86400"))

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.filebased.FileBasedCache",
        "LOCATION": os.getenv("CACHE_DIR", "/tmp/fuelup-cache"),
        "TIMEOUT": GEOCODE_CACHE_SECONDS,
        "OPTIONS": {"MAX_ENTRIES": 1000},
    }
}

