# FuelUp India

FuelUp is being rebuilt as an India-first route and fuel planning product. The
public experience accepts Indian locations, petrol or diesel, and the driver's
real tank, efficiency, starting fuel, reserve, waypoint, detour, routing
strategy, and price-quality preferences. Results use kilometres, litres, and
Indian rupees.

This repository is in an active productionization phase. The v2 API and India UI
vertical slice are implemented, but a public launch is intentionally blocked
until a permitted station catalogue and current price observations have been
loaded. FuelUp never relabels synthetic, stale, or geographic reference values
as live pump prices.

## What works now

- India-restricted Nominatim geocoding and ordered-waypoint OSRM routing.
- A configurable petrol/diesel vehicle model with reserve-safe range checks.
- Deterministic fuel-stop optimization using Decimal INR/litre arithmetic.
- Route comparison for cheapest estimated, fastest, and balanced strategies.
- Versioned OSM station snapshots with atomic activation and source identity.
- Append-only price observations, expiry, provenance, moderation state, and a
  deterministic quote resolver.
- Explicit `reported`, `reference`, `estimated`, and `stale` price labels with
  geographic precision and confidence.
- Cache keys versioned by request, station snapshot, observation watermark,
  and resolver policy; current results expire no later than their prices.
- A market-configured v2 API and India UI with no public legacy demos or units.

The production roadmap and acceptance criteria live in
[`openspec/changes/productionize-fuelup-india/`](openspec/changes/productionize-fuelup-india/).

## Architecture

```text
Browser
  |
  v
Next.js India UI ---- same-origin /api/route proxy
  |
  v
Django /api/v2/route/
  |-- India Nominatim geocoding
  |-- OSRM-compatible route alternatives
  |-- active OSM station snapshot
  |-- accepted price observations + resolver
  |-- vehicle-aware fuel optimizer
  `-- Redis/file cache
```

Backend responsibilities are separated by layer:

```text
routes/
|-- api/              HTTP validation, errors, and rate limiting
|-- application/      market configuration, orchestration, and response cache
|-- domain/           vehicle, quote, geometry, and optimizer rules
|-- infrastructure/   map clients and station/price repository
|-- management/       source registry and OSM snapshot imports
|-- migrations/       durable market catalogue and observation schema
`-- tests/            domain, repository, command, API, and legacy tests
```

## Quick start

Docker is the closest local match to deployment:

```bash
docker compose up --build
```

Open <http://localhost:3000>; the Django API is exposed on
<http://localhost:8000>.

For native development:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
python manage.py migrate
python manage.py sync_source_registry
python manage.py runserver
```

In another terminal:

```bash
cd frontend
cp .env.example .env.local
npm ci
npm run dev
```

## Load an India station snapshot

The runtime does not use the old synthetic CSV. Obtain the India or selected
zone `.osm.pbf` extract recorded in the source registry, then run:

```bash
scripts/extract_osm_stations.sh western-zone-latest.osm.pbf india-fuel.geojson
python manage.py sync_source_registry
python manage.py import_osm_stations india-fuel.geojson \
  --snapshot-version western-zone-YYYY-MM-DD \
  --generated-at YYYY-MM-DDTHH:MM:SSZ \
  --activate
```

Fuel availability is only trusted when OSM tags declare it. The optional
`--infer-common-fuels` switch exists for labelled coverage experiments and is
not suitable for launch recommendations.

The source permissions, kill switches, attribution rules, and extraction
procedure are documented in [`docs/data-sources.md`](docs/data-sources.md).
Official price sources remain disabled until automated reuse and redistribution
are permitted. Community reporting is the planned zero-cost path to
station-level current prices; it still needs its reporting, moderation,
privacy, and abuse-control phases.

## India API

```bash
curl -X POST http://127.0.0.1:8000/api/v2/route/ \
  -H 'Content-Type: application/json' \
  -H 'X-Request-ID: india-local-1' \
  -d '{
    "start": "Ahmedabad, Gujarat",
    "finish": "Vadodara, Gujarat",
    "waypoints": ["Anand, Gujarat"],
    "vehicle": {
      "fuel_type": "petrol",
      "tank_capacity": 35,
      "efficiency": 18,
      "starting_fuel": 8,
      "reserve_fuel": 3
    },
    "maximum_detour": 5,
    "strategy": "balanced",
    "price_quality": "best_available",
    "allow_stale_prices": false
  }'
```

Health endpoints:

```bash
curl http://127.0.0.1:8000/api/health/live/
curl http://127.0.0.1:8000/api/health/ready/
```

Readiness requires the cache plus an active, valid India station snapshot with
at least one compatible, accepted, unexpired price observation. The complete
contract is in [`openapi.yaml`](openapi.yaml).

## Configuration

| Variable | Purpose |
| --- | --- |
| `DJANGO_SECRET_KEY` | Required secret in production. |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated API hosts. |
| `DATABASE_URL` | SQLite locally; durable PostgreSQL in production. |
| `REDIS_URL` | Shared cache and rate-limit store. |
| `EXTERNAL_API_USER_AGENT` | Identified app/contact value for Nominatim. |
| `GEOCODE_CACHE_SECONDS` | Geocode cache lifetime. |
| `MARKET_CODE`, `MARKET_COUNTRY_CODE`, `MARKET_COUNTRY_NAME` | Active launch market identity. |
| `MARKET_CURRENCY_CODE`, `MARKET_DISTANCE_UNIT`, `MARKET_VOLUME_UNIT` | Response currency and units. |
| `PLAN_CACHE_SECONDS` | Maximum v2 plan cache lifetime. |
| `PLAN_TIME_VALUE_PER_HOUR` | Balanced-strategy time value in market currency. |
| `PLAN_STOP_PENALTY` | Balanced-strategy stop penalty in market currency. |
| `STATION_SOURCE_SLUG`, `GEOCODING_SOURCE_SLUG`, `ROUTING_SOURCE_SLUG` | Governed provider selections. |
| `ROUTE_RATE_LIMIT_REQUESTS` | Requests allowed per client/window. |
| `ROUTE_RATE_LIMIT_WINDOW_SECONDS` | Rate-limit window. |

## Verification

```bash
.venv/bin/python -m ruff check fuelup routes scripts manage.py gunicorn.conf.py
.venv/bin/python -m coverage run manage.py test --noinput
.venv/bin/python -m coverage report
.venv/bin/python manage.py check
.venv/bin/python manage.py makemigrations --check --dry-run
.venv/bin/python scripts/validate_manifests.py

cd frontend
npm run lint
npm run typecheck
npm run build
npx playwright install chromium
npm run test:browser
```

OpenSpec validation:

```bash
openspec validate productionize-fuelup-india --strict
```

The backend suite uses the configured database. CI covers PostgreSQL and SQLite;
four restore checks require PostgreSQL and matching `pg_dump`/`pg_restore` tools.
Browser checks cover desktop, mobile, and keyboard flows with synthetic contract
fixtures and blocked external requests. They require a production build first.

Read the [verification record](docs/verification-2026-10-27.md),
[provider incident runbook](docs/provider-operations.md), and
[database recovery procedure](docs/database-recovery.md) for evidence and
operational limits. The automated restore drill is available through
`.venv/bin/python manage.py verify_database_restore` on a trusted PostgreSQL
maintenance host.

## Current release blockers

- No enabled station-level price feed is being presented as live.
- A real India/zone OSM snapshot has not been committed or imported by default.
- Community reporting, moderation, abuse controls, and privacy flows are not yet
  implemented.
- Public free geocoding/routing services have no production SLA; provider
  budgets, circuit breakers, and a launch pilot still need validation.
- Selected fuel-stop driveway detours are estimated until the bounded waypoint
  validation phase is implemented.

The previous exercise API remains isolated for compatibility testing during the
OpenSpec migration window. It is not used by the public frontend or deployment
cache warmup and is scheduled for removal in task 11.5.
