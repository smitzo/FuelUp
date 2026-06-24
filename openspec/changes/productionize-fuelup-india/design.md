## Context

FuelUp currently combines Nominatim, the public OSRM demo service, an enriched
U.S. CSV, and a deterministic fixed-route optimizer. The code already has useful
domain/application/infrastructure boundaries, caching, rate limiting, health
checks, containers, and tests. The product contract is still an exercise: U.S.
locations, approximate city coordinates, synthetic/static prices, USD/gallon,
and one fixed vehicle.

The first real market is India. Drivers need INR/litre estimates for petrol or
diesel based on their own vehicle. They must be able to tell whether a number is
an actual recent station report, an official city/state reference, an estimate,
or unavailable.

The hard constraint is zero paid APIs and zero paid infrastructure. That makes
production-quality software possible for a bounded pilot, but rules out a
commercial SLA, unlimited traffic, and a licensed nationwide real-time pump
price feed. The primary stakeholders are drivers, community price reporters,
moderators/operators, and maintainers responsible for provider terms and data
quality.

## Goals / Non-Goals

**Goals:**

- Replace the public product surface with an India-only, INR/litre,
  kilometre-based contract.
- Produce useful plans for configurable petrol and diesel vehicles.
- Make data provenance and uncertainty visible and machine-readable.
- Build a legal, replaceable, no-paid-provider data path and a community loop
  for station-level freshness.
- Preserve deterministic optimization and bounded external-call costs.
- Degrade honestly when sources are stale, incomplete, quota-limited, or down.
- Add the product, security, data, and operational gates needed for a public
  pilot.

**Non-Goals:**

- U.S. or global coverage in this change.
- Claims of real-time traffic, guaranteed pump price/availability, or a
  commercial availability SLA.
- Scraping websites, automating SMS, or using undocumented OMC endpoints without
  written terms or permission that allow the intended use.
- Fuel payments, delivery, fleet dispatch, advertising, or marketplace ranking.
- Native mobile apps; the first client remains a responsive PWA-capable web app.
- Offline map-tile downloads from OpenStreetMap's public tile service.

## Decisions

### 1. Launch India-only behind a versioned API contract

Create `/api/v2/route/` and India-oriented station/report endpoints rather than
silently changing v1 fields. V2 accepts:

- origin, destination, and optional waypoints;
- `fuel_type` (`petrol` or `diesel`) and optional grade;
- tank capacity in litres, efficiency in km/litre, starting fuel, and reserve;
- maximum station detour and supported route preferences; and
- a price-quality policy (`best_available` or `station_reported_only`).

Domain math uses kilometres, litres, km/litre, and `Decimal` INR. Provider units
are converted only at infrastructure boundaries. V2 responses include both the
selected route and comparison summaries, plus a data-quality summary.

**Alternative considered:** mutate v1 in place. Rejected because cached clients,
fixtures, and field meanings would break invisibly.

### 2. Separate stations, observations, and resolved quotes

The CSV row currently conflates station identity, location, and price. Replace
it with three concepts:

```text
Station
  stable_id, source_ids, name/brand, exact-or-approximate coordinate,
  address, supported fuels, operating status, provenance, last_seen_at

PriceObservation (append-only)
  station_id nullable, geography_type/id, fuel type/grade, INR/litre,
  source type/id, observed/effective/received/expiry times,
  validation state, contributor pseudonym, evidence metadata

ResolvedPriceQuote (computed, immutable input to one plan)
  chosen value, precision, label, confidence, freshness,
  contributing observation ids, resolution policy/version
```

Source types are `official_reference`, `community_report`, `model_estimate`, and
`demo`. User-visible price labels are `reported`, `reference`, `estimated`,
`stale`, and `unavailable`. `live` is reserved for a future provider that both
supplies station-level current data and permits that label; no planned source
qualifies today.

A city/state reference remains city/state precision even when used to estimate a
station cost. The API never rewrites it as a station observation. The plan
summarizes what percentage of estimated spend came from each label.

**Alternative considered:** overwrite one current price per station. Rejected
because it destroys provenance, makes moderation irreversible, and hides stale
or low-precision fallbacks.

### 3. Resolve prices with explicit freshness and confidence

The resolver filters observations by fuel/grade, validation state, effective
time, expiry, and geographic applicability. It then prefers, in order:

1. a permitted fresh official station observation, if one becomes available;
2. a consensus of independent fresh community station reports;
3. one plausible fresh community station report;
4. a permitted official city/state reference displayed at that precision;
5. a model estimate derived from a dated reference; or
6. unavailable.

Community consensus uses a median and rejects outliers outside configurable
absolute and percentage tolerances. Initial proposed freshness windows are 24
hours for community reports and 36 hours for a daily official reference; these
remain configuration until the data spike measures actual update behaviour.
Expired values may support an explicitly stale estimate but never a reported or
reference label without a stale marker.

The optimizer receives resolved quotes, never raw observations. Its output is
therefore deterministic for a recorded station-catalogue version, observation
watermark, resolver version, vehicle, and route.

**Alternative considered:** choose the newest value. Rejected because a single
new malicious or erroneous report would beat corroborated data.

### 4. Use an open station catalogue and only permitted price imports

Initial station identity and coordinates come from a reproducible India
OpenStreetMap extract, preferably Geofabrik's PBF, filtered for fuel stations.
Imports retain OSM identifiers, data timestamp, coordinate precision, and ODbL
attribution. They are idempotent and produce coverage/quality reports. Missing
or suspect stations can be corrected upstream in OSM and reconciled on the next
import.

Price ingestion is gated by a source registry containing owner, terms URL,
licence/permission evidence, permitted fields, attribution, refresh budget, and
kill switch. PPAC and OMC material is a candidate official reference, not an
approved automated feed until the spike confirms reuse and automation rights.
Until then, operators may import a documented snapshot manually and community
reports provide station specificity. FuelUp will not automate IndianOil's SMS
interface or scrape its consumer page.

**Alternative considered:** call a cheap-looking unofficial fuel-price API.
Rejected because free-tier availability, provenance, redistribution rights, and
endpoint stability cannot be assumed.

### 5. Put every external map dependency behind a budgeted port

Define provider interfaces for geocoding, routing, station catalogue, price
sources, and map tiles. Each provider has configured timeouts, cache policy,
rate/concurrency budget, circuit breaker, attribution, health state, and runtime
kill switch.

For the bounded pilot:

- public Nominatim may handle user-triggered submitted searches only, globally
  capped below one request/second, with identification and durable caching;
  client-side autocomplete is not implemented;
- public OSRM may remain a development/pilot routing fallback, not an SLA-backed
  production dependency;
- a free-key routing provider such as openrouteservice is only enabled after a
  current quota/terms/India-coverage acceptance test; and
- standard OSM raster tiles are interactive and attributed, with normal HTTP
  caching but no prefetch/offline feature.

The frontend obtains provider URLs/configuration from the server so providers
can be switched without a client release. Hard counters stop calls before a
daily free quota can be exceeded. A saved plan contains GeoJSON and stop data,
not third-party tiles.

**Alternative considered:** self-host a full India geocoder, router, and tile
stack immediately. Rejected for the first zero-cost deployment because the
India extract and indexes exceed typical free-instance storage/RAM. The ports
preserve self-hosting as the scale path.

### 6. Generalize optimization and account for uncertainty

Replace constants with a validated `VehicleProfile`. Reserve fuel is never
allocated to planned consumption. Candidate stations must serve the selected
fuel, be open/unknown rather than known closed, fall within the requested
detour, and have a usable quote under the selected quality policy.

The two-stage route algorithm is:

1. obtain bounded base-route alternatives;
2. project exact station coordinates, resolve quotes, and optimize each route;
3. for the winning candidate, request at most one optional waypoint route to
   validate selected stops and detour distance when quota/provider capability
   permits; and
4. recompute totals with validated geometry, otherwise label detours and totals
   as estimated.

The response distinguishes fuel purchase cost, estimated detour fuel/time,
tolls when the provider supplies them, and generalized selection score. The UI
offers cheapest, fastest, and balanced comparisons without calling a route
“cheapest” when price coverage is below the configured threshold.

**Alternative considered:** route individually to every candidate station.
Rejected because call growth is unbounded and incompatible with free quotas.

### 7. Make cache validity follow data validity

V2 route-cache keys include normalized locations, waypoints, all vehicle and
preference fields, station-catalogue version, observation watermark/resolution
version, and API version. Cache TTL never extends beyond the earliest resolved
quote expiry. A stale cached result can be returned only on explicit degraded
fallback with `stale=true`, `as_of`, and a prominent client warning.

Provider failures use cached geocodes/routes and the latest valid station
catalogue where possible. Insufficient price coverage returns a partial estimate
or a typed `insufficient_price_data` result according to the user's quality
policy; it never invents current values.

### 8. Build community reporting as an auditable workflow

The first contribution flow accepts station, fuel/grade, INR/litre, observed
time, and optional note. Photo uploads are excluded initially to avoid storage,
privacy, and moderation cost. Reports are append-only and pass:

- schema and sensible-range validation;
- per-IP/device/account rate limits without storing raw identifiers longer than
  necessary;
- duplicate and rapid-change checks;
- comparison with recent independent reports and regional references; and
- moderation/retraction for suspicious values.

Anonymous contribution is allowed with a rotating pseudonymous token. Optional
accounts later improve reputation and cross-device saved trips. Confidence uses
independent agreement and contributor history; it does not expose reporter
identity. Accepted, rejected, superseded, and retracted states remain auditable.

**Alternative considered:** require login on day one. Rejected because it harms
the cold-start contribution loop; abuse is instead bounded and the design keeps
an upgrade path to verified contributors.

### 9. Keep personal features local-first

Vehicle garage, recent searches, favourite trips, and offline saved-plan data
are stored in the browser by default. This avoids an account and hosted-database
dependency for the basic product. Export/delete controls are included. Optional
accounts and server sync form a later slice after privacy and backup gates pass.

The PWA caches the application shell and explicitly saved plan JSON/GeoJSON.
Low-data mode avoids automatic alternative previews and minimizes map loading.
The UI is keyboard accessible, screen-reader labelled, contrast checked, and
designed for English copy with Hindi localization keys rather than hard-coded
concatenated text.

### 10. Treat zero cost as a hard operating budget

The deployment remains provider-neutral. A candidate pilot can combine a
sleeping/free web service, a free durable Postgres tier, a free small cache, and
a static/server-rendered frontend only after current terms are recorded. No
architecture claim depends on those vendors remaining free.

Required operations include Django migrations, least-privilege secrets,
structured logs without raw location histories, health/readiness, source and
quota dashboards, error/latency/data-freshness metrics, logical backups with a
tested restore, dependency scanning, rollback artifacts, and incident/runbook
documentation. Provider budgets fail closed before incurring charges; no
billing-backed API is enabled unless it has a technically enforced zero-spend
cap.

The operational target for the free pilot is measured, not promised: publish
actual availability, latency, cache hit rate, quota use, catalogue age, price
coverage, and report rejection rate. Capacity is gated by an invite/region or
request limit when free resources are exhausted.

## Zero-cost Data Source Matrix

| Need | Initial source | What it can honestly provide | Key constraint |
| --- | --- | --- | --- |
| Station locations | Geofabrik India OSM extract | Open station catalogue, coordinates, tags, timestamp | ODbL attribution/share-alike obligations; completeness varies |
| Official price baseline | PPAC/OMC material after permission review | Dated state/city/OMC reference | Not a documented station-level API; reuse/automation must be approved |
| Station price | Community reports | Recent station observation | Cold start, fraud, staleness, moderation |
| Geocoding | Public Nominatim for bounded pilot | Submitted India place search | Max 1 request/s, no autocomplete, cache and switchability required |
| Routing | Public OSRM fallback or validated free-key provider | Road geometry and duration | Best effort/free quota, no SLA; must be replaceable |
| Map | Standard OSM raster tiles for interactive pilot | Attributed interactive basemap | No offline prefetch/bulk download; best effort |

## Delivery Slices

1. **Data/legal proof:** source registry, licence evidence, small India station
   import, candidate price samples, provider quota tests, and coverage report.
2. **India core:** v2 units and vehicle model, India geocoding, deterministic
   quote resolver, India station catalogue, honest estimated/reference results,
   new UI, contract and migration tests.
3. **Community freshness:** report API/UI, moderation, consensus, audit, data
   quality dashboard, and safe expiry.
4. **Driver product:** local vehicle garage, comparisons, waypoints/preferences,
   sharing, saved plans, PWA shell, low-data mode, accessibility, and localization
   foundations.
5. **Pilot hardening:** durable deployment, restore drill, quota/circuit-breaker
   tests, security/privacy review, load test, runbooks, staged rollout, and public
   coverage/status page.

Each slice has an independent release gate. The team does not build later
features until the price-source and station-coverage spike proves a useful pilot
area.

## Risks / Trade-offs

- **No permitted free nationwide station-price feed** -> Launch with truthful
  references/estimates plus community reports; narrow coverage rather than
  mislabel data.
- **Community cold start or manipulation** -> Seed only permitted references,
  show confidence, use quorum/median/outlier rules, rate limits, reputation, and
  moderation; never rank sponsors.
- **Incomplete/stale OSM stations** -> Publish coverage age, accept corrections,
  reconcile imports, and gate supported corridors on measured coverage.
- **Public provider withdrawal/quota exhaustion** -> Ports, caching, hard
  budgets, circuit breakers, degraded cached mode, and operator kill switches.
- **Free hosting sleeps or loses ephemeral data** -> Keep canonical reports in a
  durable database, package reproducible station snapshots, test restores, and
  state that the pilot has no SLA.
- **ODbL or government-data terms are mishandled** -> Maintain a source registry,
  attribution manifest, generated-data notices, and a release-blocking licence
  review.
- **Route optimizes an estimated rather than actual pump price** -> Display the
  coverage mix and confidence, allow station-reported-only mode, and avoid a
  definitive cheapest claim below threshold.
- **Station detour is understated** -> Validate the selected stop sequence with
  one bounded waypoint route when possible; otherwise label the detour estimate.
- **Anonymous reports create privacy/abuse risk** -> Minimize identifiers, rotate
  pseudonyms, define retention, rate-limit, audit moderation, and provide
  deletion/contact flows.
- **Feature breadth delays the useful core** -> Enforce delivery slices and data
  viability gates; saved accounts, alerts, Hindi copy, and richer evidence stay
  behind the core release.

## Migration Plan

1. Add source-registry and India data models with Django migrations while v1
   remains available for internal comparison.
2. Build a deterministic importer and commit/version a compact India station
   fixture for test and initial deployment; record OSM attribution and snapshot
   time.
3. Add quote resolution and generalized optimizer tests before exposing HTTP.
4. Add `/api/v2/` and update `openapi.yaml`; run v1/v2 contract tests and replay
   fixed fixtures to verify monetary math.
5. Ship the India frontend behind a server-side feature flag. Do not display the
   U.S. demos or accept U.S. locations in the public product.
6. Enable only sources whose registry entries pass legal, quota, quality, and
   failure tests. Begin with one or more coverage-gated Indian pilot regions.
7. Add community reporting in shadow mode, inspect rejection/consensus metrics,
   then allow validated observations to influence quotes.
8. Run backup restore, provider outage, load, accessibility, security, and
   rollback drills before public pilot.
9. After the compatibility window, remove U.S. runtime data and v1 public
   routing; retain minimal synthetic fixtures only where tests require them.

Rollback uses the prior deployment artifact and database-compatible feature
flags. New observation rows are append-only and need not be deleted on rollback.
Station imports retain the previous active snapshot so a bad import can be
atomically deactivated. A rollback must never re-enable the U.S. product
publicly; it returns the India pilot to maintenance mode or its prior India
version.

## Open Questions

- Which PPAC/IOCL/BPCL/HPCL datasets, if any, explicitly permit automated reuse
  and redistribution in FuelUp? This blocks automated official-price ingestion.
- Which Indian city/corridor has enough OSM station completeness and initial
  reporters for the first coverage-gated pilot?
- What measured update cadence should set community and official freshness
  windows?
- Which free routing/geocoding deployment combination passes India coverage,
  quota, latency, and terms tests without billing risk?
- Should the first community pilot stay anonymous or invite a small set of
  verified contributors?
- What price-confidence threshold is required before the UI may use “cheapest”
  rather than “lowest estimated cost”?

## Verified Research References (2026-08-10)

- IndianOil states that indicative petrol/diesel prices change at 6 a.m., use a
  dealer-code SMS flow, and may vary by outlet:
  https://iocl.com/petrol-diesel-price
- PPAC links state RSP/price build-up material from IOC, BPC, and HPC:
  https://ppac.gov.in/retail-selling-price-rsp-of-petrol-diesel-and-domestic-lpg/price-build-up-of-petrol-and-diesel
- Geofabrik publishes an India OpenStreetMap extract under ODbL:
  https://download.geofabrik.de/asia/india.html
- Public Nominatim is limited to an absolute maximum of one request/second,
  requires identification/caching/switchability, and forbids client
  autocomplete:
  https://operations.osmfoundation.org/policies/nominatim/
- Standard OSM tiles are best effort and prohibit offline prefetch/bulk
  downloading:
  https://operations.osmfoundation.org/policies/tiles/
