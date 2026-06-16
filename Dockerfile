FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    DJANGO_SETTINGS_MODULE=fuelup.settings.production \
    PORT=8000

WORKDIR /app

RUN groupadd --system fuelup \
    && useradd --system --gid fuelup --home-dir /app fuelup

COPY requirements.txt .
RUN python -m pip install --upgrade pip \
    && python -m pip install -r requirements.txt

COPY --chown=fuelup:fuelup . .
RUN chmod +x docker/backend-entrypoint.sh \
    && mkdir -p /app/staticfiles \
    && chown -R fuelup:fuelup /app

USER fuelup

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import os, urllib.request; request = urllib.request.Request('http://127.0.0.1:' + os.getenv('PORT', '8000') + '/api/health/live/', headers={'X-Forwarded-Proto': 'https'}); urllib.request.urlopen(request, timeout=3)"

ENTRYPOINT ["./docker/backend-entrypoint.sh"]
