import os

from fuelup.settings.base import *  # noqa: F403
from fuelup.settings.base import env_bool

DEBUG = False
SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]

SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", True)
SECURE_HSTS_SECONDS = 31_536_000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
TRUST_PROXY_HEADERS = True
LOGGING["root"]["handlers"] = ["json"]  # noqa: F405
LOGGING["loggers"]["fuelup"]["handlers"] = ["json"]  # noqa: F405
