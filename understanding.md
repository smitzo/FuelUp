# Understanding the FuelUp Project

> This `understanding.md` was created with AI so that a complete beginner can
> understand the project. Smit provided the scratch understanding/context; the
> rest was AI-generated and then modified.

## 1. What does FuelUp do?

A driver supplies two U.S. locations:

```json
{
  "start": "Los Angeles, CA",
  "finish": "New York, NY"
}
```

FuelUp returns:

- A road route.
- A blue highlighted map path.
- Fuel stations in driving order.
- Gallons to buy at each stop.
- Total estimated fuel cost.

The vehicle assumptions are fixed by the project:

```text
maximum range = 500 miles
fuel economy  = 10 miles per gallon
tank capacity = 500 / 10 = 50 gallons
```

## 2. The production architecture

```text
Browser
  |
  v
Next.js on Vercel
  |
  | server-side /api/route proxy
  v
Django on Render
  |
  +--> Redis
  |      route cache
  |      geocode cache
  |      rate-limit counters
  |
  +--> Nominatim: text to coordinates
  +--> OSRM: route alternatives in one call
  +--> Local CSV-derived station dataset
```

The browser never needs to know the private backend configuration. It calls
Next.js on the same origin. The Next.js server calls Django.

## 3. Why is the backend split into layers?

The backend is not one large `views.py` file:

| Layer | Folder | Responsibility |
| --- | --- | --- |
| API | `routes/api/` | HTTP, request validation, request IDs, rate limiting. |
| Application | `routes/application/` | Workflow, response caching, route selection. |
| Domain | `routes/domain/` | Geometry and fuel optimization rules. |
| Infrastructure | `routes/infrastructure/` | OSRM, Nominatim, CSV station loading. |

This matters because the optimization code can be tested without starting a
web server or calling the internet. Provider code can also be replaced without
rewriting the optimizer.

## 4. What happens during one request?

```text
validate JSON
    |
    v
check client rate limit
    |
    v
check complete response cache
    |
    +------ cache hit ------> return immediately
    |
    v
geocode start and finish
    |
    v
make one OSRM request asking for alternatives
    |
    v
evaluate every returned route locally
    |
    v
select best generalized route score
    |
    v
cache and return JSON + GeoJSON
```

An uncached request still uses at most three external calls: two geocodes and
one route request.

Nominatim requests are serialized through a Redis-backed lock and timestamp.
That means four Gunicorn workers still behave like one polite application
instead of each worker independently sending one request per second.

## 5. Why station coordinates are prepared in advance

The supplied `fuel-prices.csv` has city/state and price data, but no latitude
or longitude.

The management command:

```bash
python manage.py build_station_data
```

joins U.S. station rows to the GeoNames U.S. postal dataset and writes
`data/fuel-stations.csv`.

This is done once. Geocoding thousands of stations during every request would
be slow, expensive, and abusive to a public geocoder.

## 6. How stations are matched to the route

A route is a sequence of line segments.

The weak approach is to find the closest route vertex. That can be inaccurate
when two vertices are far apart. A station may be close to the line between
them but far from both endpoints.

FuelUp instead:

1. Places route segments into geographic grid cells.
2. Checks only nearby segments for each station.
3. Projects the station onto each candidate segment.
4. Uses the closest projected point.
5. Calculates both perpendicular route distance and route-mile progress.

This gives more accurate ordering and range calculations while avoiding a
full station-by-segment scan.

## 7. Algorithm comparison

There is no single "best algorithm" without stating the rules. For this
project, the important rules are:

- At most one routing-provider call.
- Multiple route alternatives may be returned by that call.
- Station prices are fixed.
- The vehicle has a 50-gallon tank and constant 10 MPG.
- Stations are ordered along each candidate route.
- Fuel cost matters most, but route time and excessive stops also matter.

### Worst: enumerate every station subset

Try every possible combination of stops:

```text
station 1: stop or skip
station 2: stop or skip
station 3: stop or skip
...
```

With `n` stations this creates roughly `2^n` combinations.

| Property | Result |
| --- | --- |
| Correctness | Can be correct if fuel amounts are also optimized. |
| Complexity | Exponential, approximately `O(2^n)`. |
| Production suitability | Unusable after a modest number of stations. |

For 100 candidates, the number of subsets is astronomically large.

### Bad: stop every 500 miles

Drive close to 500 miles, then choose a nearby station.

| Property | Result |
| --- | --- |
| Correctness | Usually range-safe if station coverage exists. |
| Fuel cost | Poor because it ignores future prices. |
| Complexity | Fast, around `O(n)`. |
| Failure example | Passes cheap fuel and is forced to buy expensive fuel later. |

Fast is not useful when the decision itself is wrong.

### Okayish: cheapest station in each geographic window

Split the route into 500-mile windows and select the cheapest station in every
window.

| Property | Result |
| --- | --- |
| Correctness | Better than fixed-distance stops. |
| Fuel cost | Not globally optimal. |
| Complexity | Usually `O(n)`. |
| Failure example | The cheapest station in one window may make the next window unreachable. |

Independent windows do not understand that fuel can be carried across window
boundaries.

### Good: the previous route dynamic program

The earlier project version used dynamic programming over reachable stations.
It enforced the 500-mile limit and added a stop penalty.

| Property | Result |
| --- | --- |
| Range safety | Good. |
| Stop practicality | Good. |
| Complexity | Approximately `O(n^2)`. |
| Main flaw | It priced each leg at the previous selected station. |

That main flaw is important. Suppose cheap station A can sell enough fuel to
drive through expensive station B. The old model still charged the B-to-C leg
at B's price. Real drivers can carry fuel, so that model was not truly
cost-optimal.

### Best for a fixed route: future-cheaper fuel purchasing

For stations ordered along one route:

1. Look ahead up to 500 miles.
2. If a cheaper station exists, buy only enough to reach the first cheaper
   station.
3. If no cheaper station exists, fill enough to carry cheap fuel forward,
   limited by the 50-gallon tank.
4. If equal-price stations are reachable, target the farthest useful equal
   station so intermediate equal-price top-offs are skipped.
5. Continue until the destination.

Why this is optimal:

- Buying extra fuel before a cheaper reachable station is wasteful because the
  same gallon can be bought more cheaply later.
- Buying too little when no cheaper station is reachable forces the vehicle to
  buy more expensive fuel before necessary.
- Therefore every purchase is either the minimum needed to reach cheaper fuel
  or the maximum useful amount of currently cheaper fuel.

For `n` ordered stations and `w` stations inside a 500-mile look-ahead window,
the current implementation is approximately `O(n * w)`. In the worst dense
case this is `O(n^2)`, but the corridor dataset keeps `w` bounded in practice.
The CI suite verifies 1,000 candidates in under 500 ms.

### Best end-to-end for this project: alternatives plus exact fixed-route fuel

FuelUp asks OSRM for route alternatives in one call. It then runs the exact
fixed-route fuel policy on each alternative.

Each route receives a generalized score:

```text
actual fuel cost
+ configured value of travel time
+ configured operational penalty per fuel stop
```

Fuel cost remains the main real-money output. Time and stop penalties are used
only to avoid selecting a technically cheap route that is much slower or
operationally annoying.

This is the best fit for the project because it:

- Stays within one routing call.
- Compares more than one road route.
- Minimizes fuel purchase cost correctly on each fixed route.
- Accounts for route duration and stop count.
- Runs quickly enough for synchronous API requests.

### What would be better with different data and budget?

A global road-network optimizer could search road edges and fuel stations at
the same time using a resource-constrained shortest-path algorithm. That could
model exact station driveway detours, tolls, traffic, and live prices.

It is not the right implementation here because:

- The CSV lacks exact station coordinates.
- Exact detour routing would require many provider calls or a self-hosted road
  graph.
- It conflicts with the project's one-to-three-call requirement.

Calling a more complex algorithm "best" while feeding it approximate station
locations would create impressive-looking but misleading precision.

## 8. How route alternatives are selected

OSRM can return multiple alternatives from one request. FuelUp evaluates every
feasible alternative.

The route score is configurable:

```text
selection score =
    total fuel cost
  + route hours * ROUTE_TIME_VALUE_USD_PER_HOUR
  + fuel stops * ROUTE_STOP_PENALTY_USD
```

`total_cost_usd` contains fuel only. The time and stop values appear in route
selection metadata and are not presented as money spent at the pump.

## 9. How total fuel is checked

The physical invariant is:

```text
initial gallons + gallons bought at stops = route miles / 10
```

The optimizer also tracks fuel on arrival at every purchase. It rejects a plan
if a segment needs more fuel than is available or if station coverage has a
gap greater than 500 miles.

The source dataset may not have a station exactly at the origin. Initial fuel
is therefore priced using the cheapest nearby route station as an explicit
price reference. The response labels this assumption as
`initial_fuel_estimate`.

## 10. Caching

FuelUp has two cache levels:

1. **Geocode cache:** avoids repeatedly geocoding the same place.
2. **Complete route-plan cache:** avoids all provider calls and optimization
   for an identical normalized request.

The default route-plan TTL is 30 days. Case and repeated whitespace are
normalized, so `Austin, TX` and `  austin,   tx ` share a cache entry. Different
aliases such as `NY` and `New York, NY` are different input keys even if the
geocoder later resolves them to the same place.

Route cache keys include:

- Start and finish.
- Algorithm schema version.
- Vehicle assumptions.
- Route alternative count.
- Time and stop weighting.

A short distributed lock prevents many simultaneous identical requests from
all calling providers at once. This is called cache stampede protection.

Local development uses a file cache. Production uses Redis through
`REDIS_URL`. Render's free Key Value service has no disk persistence, so a
service restart or eviction can remove cached routes before their TTL expires.
The API exposes `X-FuelUp-Cache` and `X-FuelUp-Cache-TTL` to make this visible.

## 11. Rate limiting

The route endpoint has a configurable client quota. Production counters are in
Redis, so multiple Gunicorn workers and multiple Render instances share the
same limit.

When the limit is exceeded, the API returns:

```text
HTTP 429 Too Many Requests
Retry-After: ...
X-RateLimit-Limit: ...
X-RateLimit-Remaining: 0
```

Health checks are not rate limited.

## 12. Observability and health

Every response includes `X-Request-ID`. The same ID appears in structured
production logs with:

- Request method and path.
- Status code.
- Duration.
- Cache status.

Provider calls log latency and failure information without logging sensitive
request bodies.

Health endpoints:

- `/api/health/live/`: the process can answer HTTP.
- `/api/health/ready/`: station data and cache are usable.

## 13. Frontend behavior

The Next.js frontend is modular:

| Component | Responsibility |
| --- | --- |
| `RoutePlanner` | Request, loading, errors, selected stop. |
| `RouteForm` | Inputs, swap button, route presets. |
| `TripSummary` | Distance, duration, gallons, cost. |
| `FuelStops` | Ordered interactive stop cards. |
| `MapPanel` | Browser-only map boundary. |
| `RouteMap` | Blue cased route, markers, popups, route fit. |

Selecting a stop card moves the map to that stop. The route uses a dark casing
under a bright blue line so it remains visible over roads and labels.

## 14. Running the system

Production-like local stack:

```bash
docker compose up --build
```

Native development:

```bash
source .venv/bin/activate
python manage.py runserver
```

In another terminal:

```bash
cd frontend
npm run dev
```

## 15. Quality controls

CI runs:

- Ruff backend linting.
- 30 backend tests.
- Branch coverage with an 80% minimum.
- A 1,000-station optimizer performance test.
- Django deployment security checks.
- Next.js lint and production build.
- Production npm dependency audit.
- Render, Vercel, and Compose manifest validation.
- Backend and frontend Docker builds.

## 16. Deployment

The target topology is:

- Frontend: Vercel.
- Backend: Render Docker web service.
- Cache/rate limiting: Render Key Value.

The manifests are `frontend/vercel.json` and `render.yaml`. The full procedure
is in `docs/deployment.md`.

## 17. Honest limitations

- Station positions are approximate city/postal coordinates.
- Exact station detours are not routed.
- Fuel prices are static.
- Public map providers have no production SLA.
- Constant MPG ignores traffic, weather, elevation, and vehicle load.

These limits are surfaced because production-grade engineering includes being
clear about what the system does not know.
