# India fuel-data research

Reviewed: 26 October 2026. Scope: India, petrol and diesel, multiple cities and
individual station candidates along a route. In this document a route “node”
means a candidate fuel stop, not necessarily an OpenStreetMap node: OSM stations
can also be mapped as ways or relations.

This is a research and implementation proposal. No new provider was enabled,
no account was created, and no live price observations were imported.

## Recommendation

Use a periodically refreshed OSM station catalogue plus separately refreshed
geographic price observations. Evaluate API Mitra first for a small price pilot;
keep a provider interface so it can be replaced. Add community observations for
prices tied to individual pumps.

Real station coordinates and today's city prices can support useful trip-cost
estimates. They cannot establish which pump in the same city is cheapest. An
India-wide, permanently free, current station-price feed was not verified in
this research. Free data access also does not cover hosting or guarantee uptime.

## Source comparison

| Source | Useful data | Free-access evidence | Assessment |
| --- | --- | --- | --- |
| OSM / Geofabrik | Station geography and contributed attributes | India and regional extracts; ODbL | Recommended station catalogue; survey coverage before launch. |
| API Mitra | Petrol/diesel by city and state | Advertises a free monthly allowance; exact fuel allowance not published on the reviewed product page | First evaluation candidate, pending key, quota, provenance, and reuse checks. |
| API Express | Advertised daily city/pincode prices | Pricing lists 1,000 monthly requests; free-plan production access is unclear | Alternative candidate; sandbox explicitly uses mock values. |
| Daily Fuel Price India on RapidAPI | Advertised Indian fuel-price service | Basic listing shows 1,000/month with paid overages | Trial candidate requiring credentials and verification; enforce a local spending cap. |
| PPAC | Official metro/reference publications | Publicly readable; permission wording differs between policy pages | Useful verification reference; resolve reuse and automation before ingestion. |
| IndianOil | Indicative dealer-code price lookup | Consumer SMS instructions | Useful for individual checks; no developer feed verified. |
| DataFlag | Advertised daily city/state prices | No free allowance established on reviewed product page | Consider if a paid provider becomes acceptable. |
| Community reports | Observations at a specific station | FuelUp can collect contributions under its own published terms | Best independent path to pump-specific coverage, with a cold-start problem. |

## Station locations

[Geofabrik India](https://download.geofabrik.de/asia/india.html) provides country
and zone extracts. At review time the full PBF was about 1.6 GB; the Western Zone
was about 211 MB. A western-region pilot is a smaller starting point than the
whole country. These are map snapshots, not live pump availability.

Retain source object type and ID, coordinates, name, brand, available address
fields, declared fuels, and snapshot time. Missing opening hours, fuel tags, or
addresses must remain unknown until verified. OSM coordinates do not necessarily
identify a routable entrance on the correct side of a divided highway.

FuelUp already provides `scripts/extract_osm_stations.sh` and
`import_osm_stations`. Preserve node/way/relation identity and deduplicate
multiple objects representing one outlet. Confirm that exported objects retain
the source ID format the importer expects.

Use stored extracts for regular route requests. Overpass can support bounded
exploration after reviewing the chosen operator's policy; do not query all of
India for each trip. Its operator policy could not be fully reviewed here.

OSM requires attribution and compliance with the ODbL, including applicable
share-alike obligations for derived databases. See
[OSM copyright and licence](https://www.openstreetmap.org/copyright).

## Price API findings

### API Mitra: evaluate first, access not yet validated

The [fuel documentation](https://docs.apimitra.in/fuel/overview/) describes city
and state observations, both fuels in a response, and five daily crawls.
Documented endpoints worth testing with a key:

| Endpoint | Intended use |
| --- | --- |
| `/fuel/cities` | Discover the actual supported locations. |
| `/fuel/latest` | Batch prices for the documented 13 popular cities. |
| `/fuel?city=mumbai` | One city. |
| `/fuel?state=west+bengal` | A state reference and nested cities. |
| `/fuel/status` | Upstream crawl health. |

These are documentation claims, not successful authenticated checks. The docs
and homepage disagree on coverage counts and authentication. The
[product page](https://www.apimitra.in/api/fuel) describes an unspecified free
monthly allowance and key signup, while the homepage also advertises no-key
access. The [rate-limit page](https://docs.apimitra.in/reference/rate-limits/)
still describes no-key access and 60 fuel requests/minute.

A direct, unauthenticated request to `https://api.apimitra.in/fuel` on
26 October 2026 at 11:26 UTC returned HTTP 401:

```json
{
  "error": "API key required. Get one from https://apimitra.in (x-api-key header or ?key=)",
  "code": "api_key_required"
}
```

No price response, freshness, accuracy, or free quota was verified. Published
examples are not current-price evidence. Confirm caching/display permission,
underlying source rights, and whether timestamps mean source observation time
or merely crawl time before accepting the feed.

### API Express: distinguish sandbox from current data

The [price product](https://www.apiexpress.in/apis/fuel-price) advertises daily
Indian city/pincode prices and a batch query. Its
[pricing page](https://www.apiexpress.in/pricing) lists 1,000 monthly free calls,
but explicitly lists production keys on the paid plan. Conversely, the
[sandbox documentation](https://www.apiexpress.in/docs/sandbox) says signup
issues both key types. It also confirms sandbox data is fabricated for testing.

Keep this candidate pending an authenticated production response and confirmation
of free production eligibility. The
[terms](https://www.apiexpress.in/terms) permit product integration in general;
the reviewed material did not establish our intended cache retention. Do not
interpret a successful sandbox integration as removal of hardcoded prices.

### RapidAPI and other aggregators

[Daily Fuel Price India pricing](https://rapidapi.com/tango-api-tango-api-default/api/daily-fuel-price-india1/pricing)
advertises 1,000 monthly Basic requests, then $0.001/request overage, with a
separate bandwidth allowance. This is a listing claim; endpoint payloads,
coverage, freshness, and reuse were not authenticated or verified.
[RapidAPI's plan documentation](https://rapidapi-enterprise-hub.readme.io/docs/api-pricing)
explains that freemium APIs can require a payment card and charge overages.
Use only with a persistent, atomic local quota counter and a hard stop.

[DataFlag](https://dataflag.in/products/fuel-price) advertises daily city/state
prices; a free allowance was not established.
[Zyla](https://www.zylalabs.com/api-marketplace/market%2Bdata%2B%26%2Btrading/fuel%2Bprices%2Bin%2Bindia%2Bapi/324)
offers trial calls followed by paid plans, so it is not a sustained zero-cost
baseline. Public GitHub scraper projects are implementation examples, not proof
of a maintained feed or permission to redistribute the underlying data.

## Official references

[IndianOil](https://iocl.com/petrol-diesel-price) says daily changes take effect
at 6 a.m. and explains dealer-code SMS lookups. It explicitly describes the
results as indicative and warns that prices vary between outlets. This consumer
flow does not establish a free automated station-price API.

[PPAC metro prices](https://ppac.gov.in/retail-selling-price-rsp-of-petrol-diesel-and-domestic-lpg/rsp-of-petrol-and-diesel-in-metro-cities-since-16-6-2017)
provide an official comparison source. Its
[terms](https://ppac.gov.in/terms-conditions) allow accurate reproduction with
attribution, subject to third-party rights. However, its separate
[website copyright policy](https://ppac.gov.in/website-policies) additionally
requires permission by email. Automated ingestion and redistribution remain
unresolved; do not enable the existing registry entry based solely on the more
permissive page. No permission request was sent during this research.

Government datasets should be evaluated by resource, observation date, and
geographic resolution. The presence of historical petrol/diesel tables on
data.gov.in does not establish a daily station feed; none was verified here.

## Routing and geocoding

The India frontend already proxies `/api/v2/route/`. Existing configuration uses
India, INR, kilometres and litres. The old US explainer in `understanding.md`
describes the earlier exercise and is not the current frontend architecture.

For a bounded pilot, retain the existing Nominatim client only under the
[public usage policy](https://operations.osmfoundation.org/policies/nominatim/):
at most one request/second across the whole application, identified requests,
caching, attribution, user-submitted searches, and no autocomplete or systematic
station reverse-geocoding. It is not a service with guaranteed capacity.

[Openrouteservice](https://openrouteservice.org/) offers a free Standard key.
Its [official FAQ](https://giscience.github.io/openrouteservice/frequently-asked-questions)
describes default directions limits of 2,000/day and 40/minute, with account
quota headers and server-side key handling. Confirm the account allocation
before implementation. This is a routing candidate, not a fuel-price source or
verified live-traffic feed. It needs its own adapter and validation of waypoint,
alternative-route, and detour limits; changing the OSRM base URL is insufficient.

The project registry currently disables the public OSRM demo for production.
Keep that distinction. A self-hosted routing engine avoids hosted API quotas,
but still consumes paid or locally supplied compute.

## How different fuel-stop nodes should receive prices

Keep station identity separate from price geography. Two pumps in one city may
share one city reference until an observation actually identifies an outlet.

| Node | Available evidence | Display and optimization interpretation |
| --- | --- | --- |
| Pump A in city X | Current city X quote | City reference, low confidence. |
| Pump B in city X | Same city X quote | Same reference; no evidence A or B is cheaper. |
| Pump C in city Y | Current city Y quote | City Y reference; estimated cross-city comparison. |
| Pump D | Recent validated station report | Station-reported price, with report time and confidence. |
| Pump E | No applicable current quote | Price unavailable; exclude from priced optimization. |

Resolve applicable prices in the existing order: direct official station
reference, validated station reports, geographic reference, explicit estimate,
then opt-in stale data. Continue distinguishing evidence type from geographic
precision. A state reference must not become a city or station observation.

Store source identity, geographic scope, fuel/grade, Decimal INR/litre value,
source observation time, effective time, fetch time, expiry, and validation
state. Repeatedly fetching an old observation must not extend its validity.

The current code needs these changes for a provider integration:

1. **Third-party provenance:** `SourceType` has official reference, community,
   model estimate, and demo only. Add a third-party reference category and update
   the resolver/import path; do not mark an aggregator official merely because
   it claims official upstream sources. The existing local importer always
   writes `official_reference`.
2. **Geographic identity:** current reference matching casefolds strings but has
   no parent-state key or alias catalogue. Add scoped IDs and explicit aliases
   such as Bengaluru/Bangalore; reject ambiguous matches. The OSM importer only
   copies existing `addr:*` fields. Enrich missing geography from reviewed
   boundary data with a local spatial join rather than bulk public geocoding.
3. **Fuel and grade coverage:** measure declared fuel coverage. Preserve unknown
   fuel support and premium/regular distinctions; never infer prices from brand.
4. **Refresh worker:** add a provider interface and scheduled import command with
   source checks, timeouts, persistent request accounting, bounded retries,
   idempotent imports, and provider health. Fetch once for many users, outside
   the route request. Keep keys on the backend.
5. **Freshness and caching:** expire by source effective time and a documented
   daily policy, invalidate plans through observation watermarks, and do not
   silently substitute fabricated prices during an outage.
6. **Route access:** separately validate selected stops' road access and actual
   added driving distance; straight-line proximity does not prove accessibility.

## Pilot and budget

Proposed first corridor: Ahmedabad–Vadodara, followed by a route crossing a state
boundary. These are test targets, not claims that the shortlisted provider
covers those cities. Use `/fuel/cities` to establish coverage first; if either
city is absent, use another covered corridor or change provider.

A hypothetical 1,000-request monthly allowance can support:

| Fetch pattern | Maximum calls in a 31-day month, before retries |
| --- | ---: |
| One batch per day | 31 |
| One batch per day per fuel, two fuels | 62 |
| Twenty city requests per day, both fuels together | 620 |
| Twenty cities per day, one request per fuel | 1,240 |

Batch size, response coverage, and whether billing counts HTTP requests or
records require confirmation. Reserve quota for retries and discovery; budget
across all workers and environments. Do not assume an unspecified free tier
provides 1,000 calls.

Before implementing the first price adapter, obtain a developer key through the
provider's account flow and establish the free production allowance and reuse
terms. Then check actual city coverage, a same-day observation against an
independent outlet/reference, timezone and grade handling, and several days of
updates. An unchanged price alone is not evidence of stale data.

Implementation acceptance should include a real OSM snapshot, measured station
and declared-fuel coverage, correctly scoped provider observations, refresh
deduplication, stale-data behavior, hard quota enforcement, UI provenance, and
an end-to-end India route. Unit fixtures can verify logic but cannot validate
provider freshness or coverage.
