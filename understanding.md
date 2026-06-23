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

The frontend also bundles 25 illustrative demo routes. These use the normal
result components but make no Django request, so an evaluator can explore the
map, fuel stops, and totals while Render's free service is asleep. Demo results
are labeled clearly and never replace the live optimizer silently.

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

### The same request, traced through the actual files

Suppose Postman sends:

```http
POST /api/route/
Content-Type: application/json

{
  "start": "Austin, TX",
  "finish": "Dallas, TX"
}
```

The backend processes it in this order:

1. **Request ID middleware**

   `routes/api/request_context.py` accepts a valid `X-Request-ID` header or
   creates a new ID. The ID is returned in the response and included in logs.

2. **Rate-limit middleware**

   `routes/api/rate_limit.py` counts requests from the client in Redis. If the
   configured limit is exceeded, it returns HTTP `429` before doing expensive
   route work.

3. **HTTP validation**

   `routes/api/views.py` parses JSON and verifies that `start` and `finish` are
   non-empty strings of at most 300 characters. Bad input becomes a structured
   HTTP `400` error.

4. **Complete route-plan cache**

   `routes/application/plan_cache.py` normalizes the two strings and creates a
   SHA-256 cache key. If the complete response already exists, the backend
   returns it immediately with:

   ```text
   X-FuelUp-Cache: HIT
   ```

   A cache hit makes **zero Nominatim calls, zero OSRM calls, and does not run
   station matching or fuel optimization again**.

5. **Geocode both locations**

   On a route-cache miss, `routes/infrastructure/map_client.py` converts
   `Austin, TX` and `Dallas, TX` into coordinates using Nominatim. Each
   geocode has its own cache, so zero, one, or two geocoding calls may be
   needed.

   The request includes `countrycodes=us`. A place outside the supported U.S.
   coverage becomes `location_not_found`.

6. **Request road-route alternatives**

   The same map client makes one OSRM request using the two coordinates. It
   asks for driving alternatives and simplified GeoJSON geometry. This is one
   routing call regardless of how many alternatives OSRM returns.

7. **Load local station prices**

   `routes/infrastructure/station_repository.py` reads the prepared
   `data/fuel-stations.csv`. This is local file access, not an external API
   call. The parsed station tuple is cached in process memory.

8. **Match stations to each route**

   `routes/domain/geometry.py` projects station coordinates onto route
   segments. It keeps stations within the 25-mile candidate corridor and
   records each station's route mile.

9. **Build the cheapest fuel plan for each alternative**

   `routes/domain/optimizer.py` checks that no station gap exceeds 500 miles,
   tracks fuel remaining, and decides how many gallons to buy at each useful
   station.

10. **Score route alternatives**

    `routes/application/planner.py` adds the route's fuel cost, time weighting,
    and stop penalty. Alternatives that cannot produce a range-safe fuel plan
    are rejected.

11. **Choose and serialize the winner**

    The route with the smallest selection score wins. It is converted into the
    JSON structure seen in Postman: locations, route, vehicle, fuel plan, and
    metadata.

12. **Cache and return**

    The complete JSON plan is cached for the configured TTL and returned with
    cache, rate-limit, and request-ID headers.

### Exactly how many external API calls happen?

| Situation | Nominatim | OSRM | Total external calls |
| --- | ---: | ---: | ---: |
| Complete route cache hit | 0 | 0 | 0 |
| Route miss, both geocodes cached | 0 | 1 | 1 |
| Route miss, one geocode cached | 1 | 1 | 2 |
| Completely uncached request | 2 | 1 | 3 |

Redis, the station CSV, geometry code, and the optimizer are internal
dependencies, not external map API calls.

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

### There is no confidence percentage

FuelUp does **not** calculate an AI confidence, probability, accuracy
percentage, or prediction confidence.

The field:

```text
metadata.selection_score_usd
```

is a deterministic **route comparison score**. The `_usd` suffix means all
three terms are converted into dollar-like weighting units so they can be
added. It does not mean the score is the amount charged to the driver.

With the default configuration:

```text
ROUTE_TIME_VALUE_USD_PER_HOUR = 8
ROUTE_STOP_PENALTY_USD = 4
```

consider two simplified alternatives:

| Alternative | Fuel cost | Time | Stops |
| --- | ---: | ---: | ---: |
| Route A | $70 | 4 hours | 2 |
| Route B | $76 | 3 hours | 1 |

Route A:

```text
$70 fuel
+ 4 hours * $8
+ 2 stops * $4
= $110 selection score
```

Route B:

```text
$76 fuel
+ 3 hours * $8
+ 1 stop * $4
= $104 selection score
```

Route B wins even though its pump cost is $6 higher, because it saves one hour
and one stop under the configured product policy.

The response still reports:

```text
fuel_plan.total_cost_usd = 76
metadata.selection_score_usd = 104
```

Only `$76` is estimated fuel spending. `$104` is used internally to compare
alternatives.

The final comparison order in `planner.py` is:

1. Lowest `selection_score`.
2. If tied, lowest actual `total_fuel_cost`.
3. If still tied, shortest `duration_hours`.

### What does "best route" mean here?

It means:

> The lowest-scoring feasible alternative returned by the single OSRM call,
> using the configured fuel, time, and stop policy.

It does not claim that every possible road in the United States was searched.
OSRM supplies a small set of alternatives; FuelUp evaluates those alternatives
carefully.

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
- OSRM geometry detail.
- Time and stop weighting.

A distributed lock prevents simultaneous identical requests from all calling
providers at once. Followers wait up to 15 seconds for the first result and
then return it as a cache hit. If Redis is unavailable, requests fail open and
compute immediately instead of waiting on a lock that does not exist. This is
called cache stampede protection.

Local development uses a file cache. Production uses Redis through
`REDIS_URL`. Render's free Key Value service has no disk persistence, so a
service restart or eviction can remove cached routes before their TTL expires.
The API exposes `X-FuelUp-Cache` and `X-FuelUp-Cache-TTL` to make this visible.

OSRM is requested with `overview=simplified`. In a Los Angeles to New York
profile, `overview=full` returned about 65,000 coordinates across two routes,
took about 15 seconds to download, and required another 3.4 seconds for station
projection. The simplified response returned 91 coordinates, downloaded in
about 0.9 seconds, and projected stations in about 0.18 seconds. The map still
receives a continuous GeoJSON LineString, and the 25-mile station corridor is
much wider than the visual simplification tolerance.

Production also runs `warm_route_cache --best-effort` before Gunicorn starts.
This precomputes the three frontend presets (Los Angeles to New York, Austin
to Denver, and Seattle to Miami). A cache hit makes repeat startups cheap; a
provider failure is reported but does not prevent the API from starting.

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

## 13. Understanding the Postman response

Postman shows two different parts of an HTTP response:

1. **Headers:** operational information about the request.
2. **Body:** the actual route and fuel-plan JSON.

### Important response headers

| Header | Beginner meaning |
| --- | --- |
| `X-Request-ID` | Unique ID used to find this request in server logs. |
| `X-FuelUp-Cache` | `MISS` means it was computed; `HIT` means a stored plan was reused. |
| `X-FuelUp-Cache-TTL` | Maximum number of seconds a complete plan may remain cached. |
| `X-RateLimit-Limit` | Maximum route requests allowed in the current window. |
| `X-RateLimit-Remaining` | Requests still available to this client. |
| `X-RateLimit-Reset` | Approximate seconds until the counter resets. |

These headers are not route data and therefore do not appear inside the JSON
body.

### Simplified successful response

The real GeoJSON coordinate list can be long, so this example shortens it:

```json
{
  "start": {
    "query": "Austin, TX",
    "display_name": "Austin, Travis County, Texas, United States",
    "latitude": 30.2672,
    "longitude": -97.7431
  },
  "finish": {
    "query": "Dallas, TX",
    "display_name": "Dallas, Dallas County, Texas, United States",
    "latitude": 32.7767,
    "longitude": -96.797
  },
  "route": {
    "distance_miles": 195.8,
    "duration_hours": 3.4,
    "geojson": {
      "type": "FeatureCollection",
      "features": [
        {
          "type": "Feature",
          "geometry": {
            "type": "LineString",
            "coordinates": [
              [-97.7431, 30.2672],
              [-96.797, 32.7767]
            ]
          },
          "properties": {
            "kind": "route",
            "distance_miles": 195.8
          }
        }
      ]
    }
  },
  "vehicle": {
    "maximum_range_miles": 500,
    "fuel_economy_mpg": 10,
    "tank_capacity_gallons": 50
  },
  "fuel_plan": {
    "initial_fuel_estimate": {
      "gallons": 19.58,
      "cost_usd": 58.74,
      "price_reference": {
        "name": "Example nearby station",
        "city": "Austin",
        "state": "TX",
        "price_per_gallon_usd": 3.0
      }
    },
    "stops": [],
    "total_gallons": 19.58,
    "total_cost_usd": 58.74,
    "currency": "USD"
  },
  "metadata": {
    "route_alternatives_evaluated": 2,
    "feasible_route_alternatives": 2,
    "selection_score_usd": 85.94,
    "selection_policy": "Minimum fuel cost plus configured time and stop penalties."
  }
}
```

The numbers above are a teaching example, not a guaranteed live Austin result.
Road data and the supplied station prices determine the real response.

### `start` and `finish`

| Field | Meaning |
| --- | --- |
| `query` | Exactly what the user typed. |
| `display_name` | Nominatim's resolved human-readable place. |
| `latitude`, `longitude` | Resolved point used to request the road route. |

### `route`

| Field | Meaning |
| --- | --- |
| `distance_miles` | Selected road-route distance, not straight-line distance. |
| `duration_hours` | OSRM's estimated driving duration. |
| `geojson` | Standard map data consumed by Leaflet. |

`geojson.type` is `FeatureCollection` because it contains multiple map
features:

- One `LineString` feature for the blue route.
- Zero or more `Point` features for selected fuel stops.

GeoJSON uses coordinate order:

```text
[longitude, latitude]
```

### `vehicle`

These are assignment assumptions, not values detected from a real vehicle:

| Field | Meaning |
| --- | ---: |
| `maximum_range_miles` | 500 miles |
| `fuel_economy_mpg` | 10 miles per gallon |
| `tank_capacity_gallons` | `500 / 10 = 50` gallons |

### `fuel_plan.initial_fuel_estimate`

The trip begins with fuel, but the source CSV may not contain a station exactly
at the starting address. FuelUp therefore:

1. Finds the cheapest useful station within the first 50 route miles.
2. If none exists there, uses the cheapest reachable station within 500 miles.
3. Uses that station's price as the origin fuel price reference.

| Field | Meaning |
| --- | --- |
| `gallons` | Fuel assigned before leaving the origin. |
| `cost_usd` | Estimated cost of that initial fuel. |
| `price_reference` | Station whose dataset price was used for the estimate. |

This price-reference station is an explicit modeling assumption. It does not
mean the driver physically begins at that station.

### `fuel_plan.stops`

`stops` is an array. A short route may have `[]` because a full tank can cover
it. A long route contains objects like:

```json
{
  "sequence": 1,
  "opis_id": "12345",
  "name": "Example Travel Center",
  "address": "I-40 Exit 100",
  "city": "Example City",
  "state": "OK",
  "latitude": 35.1,
  "longitude": -97.2,
  "route_mile": 420.5,
  "distance_to_route_miles": 2.1,
  "price_per_gallon_usd": 3.05,
  "fuel_on_arrival_gallons": 7.4,
  "gallons": 35.2,
  "cost_usd": 107.36
}
```

| Field | Meaning |
| --- | --- |
| `sequence` | Stop order: 1, 2, 3, and so on. |
| `opis_id` | Identifier from the supplied fuel-price dataset. |
| `route_mile` | Progress from the origin when this stop is reached. |
| `distance_to_route_miles` | Approximate perpendicular distance from station locality to route. |
| `price_per_gallon_usd` | Price from the supplied CSV. |
| `fuel_on_arrival_gallons` | Estimated fuel still in the tank on arrival. |
| `gallons` | Amount the optimizer recommends buying here. |
| `cost_usd` | `gallons * price_per_gallon_usd`, rounded as money. |

### Fuel totals

```text
fuel_plan.total_gallons = route.distance_miles / 10 MPG
```

```text
fuel_plan.total_cost_usd =
    initial_fuel_estimate.cost_usd
  + sum(cost_usd for every recommended stop)
```

For a 195.8-mile route:

```text
195.8 / 10 = 19.58 gallons
```

### `metadata`

| Field | Meaning |
| --- | --- |
| `external_calls` | Human-readable provider call policy. |
| `routing_provider` | OSRM supplied road routes. |
| `geocoding_provider` | Nominatim resolved text locations. |
| `station_coordinate_accuracy` | Warning that station points are city/postal approximations. |
| `route_alternatives_evaluated` | Number of alternatives OSRM returned. |
| `feasible_route_alternatives` | Alternatives with enough station coverage for 500-mile range. |
| `selection_score_usd` | Comparison score explained in section 8; not fuel spending or confidence. |
| `selection_policy` | Short description of the score policy. |
| `assumption` | Important modeling limitation about initial fuel and fixed-route optimality. |

If OSRM returns three alternatives and one contains a station-data gap greater
than 500 miles:

```text
route_alternatives_evaluated = 3
feasible_route_alternatives = 2
```

Only the two feasible alternatives compete for the lowest score.

### Error responses

Errors always use this shape:

```json
{
  "error": {
    "code": "invalid_request",
    "message": "\"start\" must be a non-empty string."
  }
}
```

Common statuses:

| HTTP status | Meaning |
| ---: | --- |
| `400` | JSON or input validation failed. |
| `422` | Location, route, or fuel plan could not be produced. |
| `429` | Client sent too many requests. |
| `502` | Nominatim or OSRM was temporarily unavailable. |

## 14. How to read `openapi.yaml`

OpenAPI is a machine-readable API contract. It is not executable route logic.
Postman, documentation generators, and client generators can read it.

### Important OpenAPI words

| OpenAPI keyword | Plain-English meaning |
| --- | --- |
| `paths` | Available URLs. |
| `post` / `get` | Allowed HTTP method. |
| `requestBody` | JSON the client must send. |
| `responses` | Possible HTTP status codes and their bodies. |
| `schema` | Rules describing a JSON object. |
| `properties` | Fields that may appear in that object. |
| `required` | Fields that must be present. |
| `type: object` | JSON `{ ... }`. |
| `type: array` | JSON `[ ... ]`. |
| `items` | Schema of each array element. |
| `type: string` | Text value. |
| `type: number` | Numeric value, including decimals. |
| `const` | Field must have exactly this value. |
| `enum` | Field must be one value from this list. |
| `$ref` | Reuse another named schema instead of copying it. |
| `additionalProperties: false` | Do not accept unknown fields. |

For example:

```yaml
RouteRequest:
  type: object
  required: [start, finish]
  additionalProperties: false
  properties:
    start:
      type: string
      maxLength: 300
    finish:
      type: string
      maxLength: 300
```

means:

```text
The request must be a JSON object.
It must contain start and finish.
Both must be strings no longer than 300 characters.
Extra fields are not part of the contract.
```

This OpenAPI fragment:

```yaml
stops:
  type: array
  items:
    $ref: "#/components/schemas/FuelStop"
```

means:

```text
stops is a JSON list.
Every item in the list has the FuelStop structure.
```

This fragment:

```yaml
vehicle:
  $ref: "#/components/schemas/Vehicle"
```

means:

```text
Look under components -> schemas -> Vehicle for the field definitions.
```

The route endpoint says:

```yaml
"/api/route/":
  post:
    requestBody: ...
    responses:
      "200": ...
      "400": ...
      "422": ...
      "429": ...
      "502": ...
```

That is the contract Postman is exercising.

## 15. Frontend behavior

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

## 16. Running the system

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

## 17. Quality controls

CI runs:

- Ruff backend linting.
- 37 backend tests.
- Branch coverage with an 80% minimum.
- A 1,000-station optimizer performance test.
- Django deployment security checks.
- Next.js lint and production build.
- Production npm dependency audit.
- Render, Vercel, and Compose manifest validation.
- Backend and frontend Docker builds.

## 18. Deployment

The target topology is:

- Frontend: Vercel.
- Backend: Render Docker web service.
- Cache/rate limiting: Render Key Value.

The manifests are `frontend/vercel.json` and `render.yaml`. The full procedure
is in `docs/deployment.md`.

## 19. Honest limitations

- Station positions are approximate city/postal coordinates.
- Exact station detours are not routed.
- Fuel prices are static.
- Public map providers have no production SLA.
- Constant MPG ignores traffic, weather, elevation, and vehicle load.

These limits are surfaced because production-grade engineering includes being
clear about what the system does not know.
