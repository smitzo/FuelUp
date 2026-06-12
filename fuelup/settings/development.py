from fuelup.settings.base import *  # noqa: F403
from fuelup.settings.base import env_bool

DEBUG = env_bool("DJANGO_DEBUG", False)

