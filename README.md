# FuelUp Route API

A Django 6 API that accepts two U.S. locations and returns:

- A drivable route as GeoJSON.
- Cost-effective fuel stops along that route.
- A fuel-cost estimate at 10 MPG.
- A plan in which every route leg is at most 500 miles.

The service uses the supplied `fuel-prices.csv`, Nominatim for geocoding, and
OSRM for routing.

## Quick start

Python 3.12 or newer is required because Django 6 requires it.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py check
python manage.py runserver
```

Check the service:

```bash
curl http://127.0.0.1:8000/api/health/
```

Plan a route:

```bash
curl -X POST http://127.0.0.1:8000/api/route/ \
  -H "Content-Type: application/json" \
  -d '{"start":"Los Angeles, CA","finish":"New York, NY"}'
```

Both inputs must resolve to locations in the United States. The API contract
is also documented in [`openapi.yaml`](openapi.yaml).

## Response shape

The response contains:

- `start` and `finish`: resolved U.S. locations.
- `route`: distance, estimated duration, and a GeoJSON `FeatureCollection`.
- `vehicle`: the fixed 500-mile range, 10 MPG, and derived 50-gallon tank.
- `fuel_plan.initial_fuel_estimate`: fuel used before the first stop, priced
  using the first selected station as the nearest available price reference.
- `fuel_plan.stops`: ordered station details, route mile, price, gallons, and
  cost.
- `fuel_plan.total_gallons`: route miles divided by 10.
- `fuel_plan.total_cost_usd`: fuel cost only.

The GeoJSON contains one `LineString` route feature followed by fuel-stop
`Point` features. It can be rendered directly by clients such as MapLibre,
Leaflet, or OpenLayers.

## Design

### External API calls

Each uncached request makes at most:

1. One Nominatim call for the start.
2. One Nominatim call for the finish.
3. One OSRM route call.

Geocodes are cached on disk for 24 hours by default. Nominatim calls are
throttled to respect its public usage policy. Station selection is entirely
local and makes no external calls.

### Station preparation

The supplied CSV has prices and city/state fields but no coordinates.
`build_station_data` enriches U.S. rows once using the GeoNames U.S. postal
dataset:

```bash
python manage.py build_station_data
```

The resulting `data/fuel-stations.csv` is committed so API startup and route
requests do not geocode thousands of stations. Data attribution is in
[`data/README.md`](data/README.md).

### Route matching and optimization

1. A spatial grid finds station cities within 25 miles of the OSRM route.
2. Duplicate city candidates are reduced to the cheapest station.
3. Dynamic programming evaluates reachable stations while enforcing a
   500-mile maximum route gap.
4. The objective combines fuel cost with an $8 operational penalty per stop.
   The penalty prevents impractical stops for tiny savings and is not included
   in `total_cost_usd`.

For a Los Angeles-to-New York integration run on June 11, 2026, the API
produced six stops for a 2,793.56-mile route. The request took about 6.3
seconds with uncached geocoding and 4.2 seconds with cached geocoding in this
development environment. Public-service latency varies.

## Configuration

Settings are controlled by environment variables listed in `.env.example`.
Important values are:

| Variable | Purpose |
| --- | --- |
| `EXTERNAL_API_USER_AGENT` | Identifies the app to Nominatim; use a real contact. |
| `GEOCODING_BASE_URL` | Replace the public Nominatim endpoint with a hosted instance. |
| `ROUTING_BASE_URL` | Replace the public OSRM demo endpoint with a hosted instance. |
| `GEOCODE_CACHE_SECONDS` | Geocode cache lifetime. |
| `EXTERNAL_API_TIMEOUT_SECONDS` | External request timeout. |

For production, use `fuelup.settings_prod`, provide `DJANGO_SECRET_KEY`, set
the real host names, and run behind an HTTPS reverse proxy:

```bash
DJANGO_SETTINGS_MODULE=fuelup.settings_prod \
DJANGO_SECRET_KEY='a-long-random-secret' \
python manage.py check --deploy
```

The public Nominatim and OSRM endpoints do not provide a production SLA.
Production deployment should self-host them or use compatible managed
services through the configurable base URLs.

## Tests

```bash
python manage.py test
python manage.py check
```

The suite covers request validation, structured errors, geocode caching,
provider parsing, spatial route matching, range gaps, fuel accounting, and an
end-to-end service response with fake map providers.

## Limitations

- The source file does not contain exact station coordinates. GeoNames
  city/postal coordinates are approximations, and the API reports each
  station's estimated distance from the route.
- Station detours are not separately routed because that would exceed the
  requested external-call budget. Range constraints use progress along the
  main route.
- Fuel prices are treated as static input data.
- Traffic, vehicle-specific road restrictions, elevation, and live closures
  are outside this exercise.

For a beginner-oriented walkthrough, read
[`understanding.md`](understanding.md).

