#!/bin/sh
set -eu

python manage.py collectstatic --noinput
python manage.py migrate --noinput

if [ "${WARM_COMMON_ROUTES:-false}" = "true" ]; then
  python manage.py warm_route_cache --best-effort
fi

exec gunicorn fuelup.wsgi:application \
  --config gunicorn.conf.py \
  --bind "0.0.0.0:${PORT:-8000}"
