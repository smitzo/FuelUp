## Why

FuelUp's optimizer is a strong technical MVP, but its U.S.-only synthetic CSV,
fixed vehicle assumptions, and unqualified prices cannot support trustworthy
real-world decisions. The next release should launch narrowly in India and make
price provenance, freshness, vehicle fit, and failure behaviour part of the
product while respecting a hard zero-paid-service constraint.

## What Changes

- **BREAKING** Replace the U.S.-only product contract with an India-only launch:
  Indian locations, kilometres, litres, km/litre, INR, petrol and diesel.
- Keep the reusable implementation market-neutral. Country restrictions,
  currency, units, scoring defaults, cache policy, and governed provider slugs
  come from one launch-market configuration; India is the first configuration,
  not a prefix copied through domain and service names.
- **BREAKING** Replace the fixed 500-mile/10-MPG/50-gallon vehicle with a
  request-selected vehicle profile containing fuel type, tank capacity,
  efficiency, starting fuel, and reserve fuel.
- Replace the synthetic station repository contract with a versioned India
  station catalogue built from legally reusable open data and precise
  coordinates where available.
- Introduce typed price observations: permitted official reference prices,
  station-level community reports, estimates, and unavailable prices. Every
  price carries source, geographic precision, observed/effective time,
  freshness, and confidence.
- Recompute or invalidate route plans when their price-data version expires;
  never return an old cached plan as current without a visible stale label.
- Add community price submission, validation, reputation, duplicate detection,
  moderation, abuse controls, and an audit trail so station-level freshness can
  improve without buying a commercial data feed.
- Add useful driver controls: vehicle garage, fuel grade, waypoints, route
  alternatives, toll/highway preferences where the routing provider supports
  them, maximum detour, cheapest-versus-fastest comparison, and shareable trip
  plans.
- Add progressive-web-app basics, low-data mode, accessibility, Indian address
  UX, English/Hindi-ready copy, and offline access to a previously saved plan.
- Add production controls for provider budgets, circuit breakers, scheduled
  ingestion, data-quality dashboards, backup/restore, privacy, security,
  observability, and graceful degradation.
- Keep all external integrations replaceable. Validate licence and automated-use
  permission before enabling any source; do not build against scraped or
  undocumented oil-company endpoints.

## Capabilities

### New Capabilities

- `india-trip-planning`: India-only location, unit, currency, fuel-type, vehicle,
  route-preference, comparison, and shareable-plan behaviour.
- `trustworthy-fuel-data`: Versioned station catalogue and price observations
  with provenance, freshness, confidence, data licensing, fallbacks, and cache
  invalidation.
- `community-price-reporting`: Safe station-price contribution, validation,
  reputation, moderation, and audit behaviour.
- `driver-experience`: Saved vehicles and trips, PWA/offline/low-data behaviour,
  accessibility, notification-ready events, and India-focused UX.
- `production-operations`: Zero-cost provider budgets, resilience, monitoring,
  backups, security, privacy, data-quality controls, and release gates.

### Modified Capabilities

None. This repository has no archived OpenSpec capabilities; the current MVP is
the implementation baseline.

## Impact

- Backend domain entities, optimizer units, route scoring, repositories,
  caching, API validation/serialization, scheduled jobs, persistence, and admin
  workflows change.
- The route API receives a versioned breaking contract and `openapi.yaml` must
  be updated; an explicit compatibility window or `/v2` endpoint is required.
- The frontend form, map, result cards, labels, attribution, stale/error states,
  saved data, accessibility, and service-worker behaviour change.
- The synthetic U.S. CSV and bundled U.S. demos stop being runtime data. They
  may remain isolated test fixtures until India fixtures replace them.
- New operational dependencies are limited to open-source components and
  permitted free services. Provider credentials, if free, remain server-side.

## Measurable Outcomes

- A driver can plan an India route for a real vehicle and petrol/diesel choice,
  with all distance, volume, efficiency, and money values in Indian units.
- Every displayed price answers: what source, what place precision, when
  observed/effective, how fresh, and whether it is reported, reference,
  estimated, stale, or unavailable.
- The system can plan with degraded providers and bounded quotas without
  silently fabricating station-level prices.
- A station-price report can be submitted, checked, moderated, expired, and
  audited without changing the deterministic optimizer.
- Release checks cover data licences, API/schema migrations, security,
  accessibility, performance, backup restore, and provider failure modes.

## Non-goals and Zero-cost Boundary

- The first launch does not support the United States or global routing.
- It does not claim real-time traffic, nationwide real-time pump prices,
  guaranteed station availability, payments, fuel delivery, fleet dispatch, or
  a commercial uptime SLA.
- A free deployment is an early production/pilot service with production-grade
  engineering, not unlimited production capacity. Growth beyond free quotas
  requires self-hosting on owned hardware, sponsorship, or an approved budget.
- PPAC/OMC city or state references are not station-level live prices. They are
  shown only at their actual precision. Community observations become stale by
  policy and are never promoted to official data.
