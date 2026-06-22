# FuelUp

FuelUp is a production-oriented route and fuel planning platform built with
Django 6 and Next.js 16. It accepts a start and finish location inside the
United States and returns:

- The best evaluated road-route alternative as GeoJSON.
- A highlighted interactive map with numbered fuel stops.
- A fuel purchase plan that respects a 500-mile vehicle range.
- Total gallons and estimated fuel cost at 10 MPG.
- Operational metadata for caching, route selection, and providers.

The backend uses the supplied `fuel-prices.csv`, GeoNames-derived station
coordinates, Nominatim geocoding, and OSRM routing. The frontend uses
TypeScript, React Leaflet, and a server-side Next.js proxy.

## Production features

- One OSRM request asks for multiple route alternatives.
- Every alternative is evaluated locally against fuel prices.
- Fuel purchasing is cost-optimal for a fixed route under the configured tank
  and MPG assumptions.
- Stations are projected onto indexed route segments instead of matched only
  to route vertices.
- Complete route responses and geocodes are cached.
- Redis-backed request rate limiting works across application instances.
- Cache stampede protection prevents duplicate provider work.
- Request IDs, structured JSON logs, liveness, and readiness probes are built
  in.
- Django and Next.js run as non-root, health-checked containers.
- Render and Vercel deployment manifests are committed.
- CI enforces linting, branch coverage, performance, dependency audit,
  deployment-manifest validation, and container builds.

## Architecture

```text
Browser
  |
  v
Next.js frontend
  |  same-origin /api/route proxy
  v
Django API
  |
  +--> Redis: route cache, geocode cache, rate-limit counters
  +--> Nominatim: start and finish geocoding
  +--> OSRM: one request containing route alternatives
  +--> Local station dataset and optimizer
```

Backend responsibilities are separated by layer:

```text
routes/
├── api/              HTTP validation, rate limiting, request context
├── application/      Route-plan orchestration and response caching
├── domain/           Entities, route geometry, fuel optimization
├── infrastructure/   Map providers and station repository
├── management/       Reproducible station-data preparation
└── tests/            Unit, integration, performance, and contract tests
```

The domain layer does not depend on Django HTTP code or provider clients. This
keeps optimization and geometry independently testable.

## Quick start

### Docker

Docker is the closest local match to production:

```bash
docker compose up --build
```

If your Docker installation uses the legacy standalone command:

```bash
docker-compose up --build
```

Open <http://localhost:3000>. Django is exposed at
<http://localhost:8000>.

The stack includes:

- Next.js frontend
- Django/Gunicorn backend
- Redis cache and rate-limit store

### Native development

Requirements:

- Python 3.12+
- Node.js 20.9+

Backend:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
python manage.py check
python manage.py runserver
```

Frontend, in another terminal:

```bash
cd frontend
cp .env.example .env.local
npm ci
npm run dev
```

Open <http://localhost:3000>.

## API usage

Health:

```bash
curl http://127.0.0.1:8000/api/health/live/
curl http://127.0.0.1:8000/api/health/ready/
```

Route plan:

```bash
curl -X POST http://127.0.0.1:8000/api/route/ \
  -H "Content-Type: application/json" \
  -H "X-Request-ID: local-test-1" \
  -d '{"start":"Los Angeles, CA","finish":"New York, NY"}'
```

Important response headers:

| Header | Meaning |
| --- | --- |
| `X-Request-ID` | Correlation ID included in server logs. |
| `X-FuelUp-Cache` | `HIT` or `MISS` for the complete route response. |
| `X-FuelUp-Cache-TTL` | Configured maximum route cache lifetime in seconds. |
| `X-RateLimit-Limit` | Requests allowed in the configured window. |
| `X-RateLimit-Remaining` | Requests remaining for the client. |
| `Retry-After` | Seconds to wait after a `429` response. |

The full contract is in [`openapi.yaml`](openapi.yaml).

## Route and fuel optimization

An uncached request makes at most three external calls:

1. Geocode the start.
2. Geocode the finish.
3. Ask OSRM for route alternatives in one routing call.

For each OSRM alternative, FuelUp:

1. Builds a spatial index of route segments.
2. Projects nearby station coordinates onto the closest segment.
3. Orders stations by accurate route-mile progress.
4. Validates that no coverage gap exceeds 500 miles.
5. Computes the minimum fuel-purchase cost for that fixed route.
6. Scores the route using fuel cost plus configurable time and stop penalties.

The fixed-route fuel policy is:

- If a cheaper station is reachable, buy only enough to reach the first one.
- If no cheaper station is reachable, carry as much cheaper fuel forward as
  the 50-gallon tank allows.
- Equal-price stations are consolidated so they do not create needless
  top-offs.

This policy is cost-optimal for an ordered fixed route with deterministic
prices, constant MPG, and no per-stop fixed charge. The route-level score then
adds operational preferences without altering the reported fuel cost.

The detailed comparison with brute force, naive greedy, the previous dynamic
program, and the selected approach is in
[`understanding.md`](understanding.md).

## Station data

The supplied CSV has station prices and city/state fields but no coordinates.
The generated `data/fuel-stations.csv` enriches U.S. rows with approximate
GeoNames postal-locality coordinates.

Regenerate it with:

```bash
python manage.py build_station_data
```

The generated data is committed so route requests never geocode thousands of
stations. Attribution and accuracy details are in
[`data/README.md`](data/README.md).

## Configuration

Copy `.env.example` and set production values through the hosting platform.

| Variable | Purpose |
| --- | --- |
| `DJANGO_SECRET_KEY` | Required secret in production. |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated API host names. |
| `DATABASE_URL` | SQLite locally or PostgreSQL URL when needed. |
| `REDIS_URL` | Shared cache and rate-limit backend. |
| `EXTERNAL_API_USER_AGENT` | Real app/contact identity for Nominatim. |
| `GEOCODE_CACHE_SECONDS` | Geocode cache TTL. |
| `ROUTE_CACHE_SECONDS` | Full route-plan cache TTL (default: 30 days). |
| `WARM_COMMON_ROUTES` | Warm the three frontend preset routes before startup. |
| `ROUTE_ALTERNATIVES` | Alternatives requested in the single OSRM call. |
| `ROUTE_GEOMETRY_OVERVIEW` | OSRM geometry detail; `simplified` is optimized for API latency. |
| `ROUTE_TIME_VALUE_USD_PER_HOUR` | Route-selection time weighting. |
| `ROUTE_STOP_PENALTY_USD` | Route-selection stop weighting. |
| `ROUTE_RATE_LIMIT_REQUESTS` | Requests per client per window. |
| `ROUTE_RATE_LIMIT_WINDOW_SECONDS` | Rate-limit window length. |

Production validation:

```bash
DJANGO_SETTINGS_MODULE=fuelup.settings.production \
DJANGO_SECRET_KEY='a-long-random-secret' \
python manage.py check --deploy
```

## Quality checks

Backend:

```bash
ruff check fuelup routes scripts manage.py gunicorn.conf.py
coverage run manage.py test
coverage report
python manage.py check
python scripts/validate_manifests.py
```

Frontend:

```bash
cd frontend
npm run lint
npm run build
npm audit --omit=dev --audit-level=high
```

Containers:

```bash
docker build -t fuelup-backend .
docker build -t fuelup-frontend frontend
```

The current suite contains 30 tests and enforces at least 80% backend branch
coverage. A performance regression test requires a 1,000-station optimization
case to complete in under 500 ms.

## Deployment

The next deployment target is already prepared:

- Django API and Redis on Render via [`render.yaml`](render.yaml).
- Next.js frontend on Vercel via
  [`frontend/vercel.json`](frontend/vercel.json).

Follow [`docs/deployment.md`](docs/deployment.md) for environment variables,
health checks, verification, and rollback.

Route plans are cached for 30 days by default. Render's free Key Value service
does not provide disk persistence, so entries can still disappear after a
cache-service restart or eviction. Check `X-FuelUp-Cache` (`HIT` or `MISS`) and
`X-FuelUp-Cache-TTL` when diagnosing a deployed request.

## Known limitations

- Station coordinates are city/postal approximations because the source CSV
  does not provide exact latitude/longitude.
- The 25-mile corridor is a candidate filter. Exact station driveway detours
  are not separately routed because doing so would violate the project's
  one-to-three external-call target.
- Fuel prices are static input data, not live prices.
- Public Nominatim and OSRM endpoints do not provide a production SLA.
  A commercial deployment should use self-hosted or contracted compatible
  providers through the configurable base URLs.
- The optimizer assumes constant 10 MPG and does not model elevation, traffic,
  weather, vehicle-specific restrictions, or price changes during the trip.
