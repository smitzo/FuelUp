# Understanding the FuelUp Project

> This `understanding.md` was created with AI so that a complete beginner can
> understand the project. Smit provided the scratch understanding/context; the
> rest was AI-generated and then modified.

## 1. What are we building?

Imagine a driver says:

> "I am driving from Los Angeles to New York. My vehicle can travel at most
> 500 miles on a tank. Where should I buy fuel, and what will the fuel cost?"

The API accepts the start and finish as text. It returns the road route, fuel
stops, and estimated fuel cost.

The request looks like this:

```json
{
  "start": "Los Angeles, CA",
  "finish": "New York, NY"
}
```

## 2. The main pieces

The project has four kinds of work:

1. **Geocoding** converts text such as `"Dallas, TX"` into latitude and
   longitude.
2. **Routing** finds the driving path between the two coordinates.
3. **Station matching** finds fuel stations close to that path.
4. **Optimization** chooses a cost-effective sequence that never leaves more
   than 500 route miles between reachable points.

Nominatim handles geocoding. OSRM handles routing. Everything involving fuel
stations and prices runs inside this Django application.

## 3. Why is station data prepared in advance?

The supplied `fuel-prices.csv` contains:

- Station name and identifier.
- Address.
- City and state.
- Price per gallon.

It does not contain latitude or longitude. A map cannot place a station using
only its city name.

The command below downloads the free GeoNames U.S. postal dataset and adds an
approximate coordinate for each U.S. station city:

```bash
python manage.py build_station_data
```

It writes `data/fuel-stations.csv`.

This preparation happens once. Doing it during every route request would mean
thousands of geocoding calls, long response times, and likely provider bans.

## 4. What happens when the API receives a request?

The request enters `routes/views.py`.

The view:

1. Checks that the body is valid JSON.
2. Checks that `start` and `finish` are non-empty strings.
3. Calls the route-planning service.
4. Returns JSON or a structured error.

The service in `routes/services.py` coordinates the complete workflow:

```text
start/finish text
        |
        v
geocode both locations
        |
        v
request one OSRM route
        |
        v
match local stations to route
        |
        v
choose fuel stops
        |
        v
build JSON + GeoJSON response
```

## 5. How are external calls kept low?

An uncached route request needs at most three calls:

1. Geocode the start.
2. Geocode the finish.
3. Get the route.

Geocoding results are cached. If the same location is requested again, Django
can read it from the cache instead of calling Nominatim again.

The app never asks a map provider to locate all 7,531 U.S. station rows during
a route request.

## 6. How are nearby stations found quickly?

Checking every route point against every station would repeat a lot of work.
The code in `routes/geometry.py` divides the map into grid cells.

Think of graph paper placed over the United States:

- Route points are placed into their grid squares.
- For each station, only nearby squares are checked.
- Stations farther than 25 miles from the route are ignored.

This is a small spatial index implemented with normal Python dictionaries. It
avoids adding a database or GIS dependency for an 8,151-row exercise dataset.

## 7. How does the fuel optimizer work?

The vehicle rules are:

```text
maximum range = 500 miles
fuel economy  = 10 miles per gallon
tank size     = 500 / 10 = 50 gallons
```

The optimizer sees stations in route order. It uses dynamic programming, which
means it remembers the cheapest known way to reach each station.

For every station, it asks:

> "Which earlier reachable station gives the lowest total score?"

A station is reachable only when the route gap is 500 miles or less.

The score contains:

```text
fuel cost + $8 for adding a stop
```

The $8 is not charged to the driver. It is only an optimization weight. Without
it, a pure price algorithm might recommend stopping for less than one gallon
just because the next station is a few cents cheaper.

After evaluating all stations, the optimizer walks backward through the saved
choices to reconstruct the selected route.

## 8. How is total fuel calculated?

The base calculation is:

```text
total gallons = route miles / 10 MPG
```

For a 1,200-mile trip:

```text
1,200 / 10 = 120 gallons
```

Each route segment is priced using its selected station's retail price. The
costs are rounded to cents and added together.

The source data may not contain a station at the exact starting location.
Therefore, fuel consumed before the first selected stop uses that first
station as the nearest available price reference. The response calls this
`initial_fuel_estimate` so the assumption is visible.

## 9. What is GeoJSON?

GeoJSON is ordinary JSON with standard shapes for maps.

The response includes:

- A `LineString` for the driving route.
- A `Point` for each fuel stop.

A frontend can pass this data to Leaflet, MapLibre, or OpenLayers to draw the
map. The backend does not need to generate a screenshot or image.

## 10. Where should I look in the code?

| File | Responsibility |
| --- | --- |
| `fuelup/settings.py` | Development settings and provider URLs. |
| `fuelup/settings_prod.py` | HTTPS-focused production settings. |
| `routes/views.py` | HTTP request validation and error responses. |
| `routes/clients.py` | Nominatim and OSRM calls. |
| `routes/geometry.py` | Distance math and station-to-route matching. |
| `routes/optimizer.py` | Range-constrained fuel-stop selection. |
| `routes/services.py` | Connects all steps and builds the response. |
| `routes/stations.py` | Loads prepared station data once per process. |
| `routes/tests/` | Automated behavior checks. |

## 11. How do I run and inspect it?

```bash
source .venv/bin/activate
python manage.py runserver
```

In another terminal:

```bash
curl -X POST http://127.0.0.1:8000/api/route/ \
  -H "Content-Type: application/json" \
  -d '{"start":"Austin, TX","finish":"Denver, CO"}'
```

Run all automated checks:

```bash
python manage.py test
python manage.py check
```

## 12. Important limitations

The prepared coordinates represent a station's city or postal locality, not
its exact driveway. That is the largest accuracy limitation.

The app also avoids routing each station detour. Routing every possible stop
would require many external calls, directly conflicting with the exercise's
one-to-three-call goal.

For a production logistics system, the next steps would be exact station
coordinates, a self-hosted or contracted routing provider, persistent shared
caching, authentication, rate limiting, metrics, and background refreshes for
fuel prices.

