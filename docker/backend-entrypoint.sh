#!/bin/sh
set -eu

python manage.py collectstatic --noinput
python manage.py migrate --noinput

exec gunicorn fuelup.wsgi:application \
  --config gunicorn.conf.py \
  --bind "0.0.0.0:${PORT:-8000}"

