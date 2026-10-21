## 1. Data, Rights, and Pilot Feasibility Gate

- [x] 1.1 Add a source-registry template covering owner, terms/permission evidence, permitted use, attribution, refresh budget, retention, and kill switch.
- [x] 1.2 Record current official terms and usage limits for Geofabrik/OSM, Nominatim, map tiles, the routing candidates, PPAC, IOCL, BPCL, and HPCL.
- [x] 1.3 Obtain or record explicit permission for each automated official-price source; mark every unresolved source disabled by default.
- [ ] 1.4 Build a one-off reproducible `amenity=fuel` extraction spike from the India OSM PBF with source ids, coordinates, brands, fuel tags, and snapshot metadata.
- [ ] 1.5 Measure station count, coordinate/tag completeness, duplicates, and route-corridor coverage for candidate Indian pilot areas and publish the report.
- [ ] 1.6 Collect permitted sample city/state references and community-style station observations to measure realistic update cadence, variation, and outliers.
- [ ] 1.7 Test candidate free geocoding/routing providers for India coverage, latency, supported preferences/waypoints, quota enforcement, and billing risk.
- [ ] 1.8 Select a coverage-gated pilot area, freshness windows, confidence thresholds, and a provider stack, or record a no-go decision before product implementation.

## 2. India Data Foundation

- [x] 2.0 Add a validated market configuration and keep reusable domain, optimizer, repository, provider, cache, API, and frontend identifiers market-neutral.
- [x] 2.1 Add Django models and migrations for source registry, station snapshot, station/source identity, and station fuel availability.
- [x] 2.2 Add append-only price observation, validation/moderation event, and active observation watermark models with database constraints and indexes.
- [x] 2.3 Add enums/value objects for fuel type/grade, source type, geographic precision, observation state, price label, freshness, and confidence.
- [ ] 2.4 Add factories and compact licensed India fixtures covering exact/approximate stations, petrol/diesel compatibility, missing prices, and multiple price classes.
- [ ] 2.5 Configure production database migrations for durable PostgreSQL while preserving SQLite development support and verify forward/backward migration paths.
- [x] 2.6 Add a generated-data attribution/licence manifest and make its validation a repository check.

## 3. Station and Price Data Pipeline

- [x] 3.1 Implement an idempotent OSM station importer that stages a snapshot, normalizes identities/tags, and emits quality metrics.
- [ ] 3.2 Implement atomic snapshot validation/activation and rollback to the previous active India catalogue.
- [ ] 3.3 Implement a registry-gated manual official-reference import format with source URL, permission record, geography, fuel, effective time, and checksum.
- [ ] 3.4 Implement deterministic observation validation for ranges, compatibility, duplicates, update velocity, geographic applicability, and outliers.
- [x] 3.5 Implement the versioned quote resolver, source priority, consensus median, freshness/expiry, stale fallback, confidence, and contributing-id trace.
- [ ] 3.6 Implement plan-level catalogue age, quote precision/label mix, unresolved count, confidence, and spend-share quality summaries.
- [ ] 3.7 Add importer/resolver replay, idempotency, outlier, expiry-boundary, bad-snapshot, and source-kill-switch tests.

## 4. India Vehicle and Optimizer Core

- [x] 4.1 Add a validated `VehicleProfile` using litres, km/litre, starting fuel, reserve, petrol/diesel, and optional grade.
- [x] 4.2 Generalize optimizer constants and calculations to vehicle inputs and Decimal INR while preserving deterministic fixed-input output.
- [x] 4.3 Filter candidates by fuel compatibility, operating status, maximum detour, quote-quality policy, and reserve-safe reachability.
- [ ] 4.4 Add cheapest-estimated, fastest, and balanced scoring summaries with documented tie-breaking and cheapest-claim coverage threshold.
- [ ] 4.5 Add one bounded selected-stop waypoint validation pass and recompute distance, time, consumption, and cost when the provider supports it.
- [ ] 4.6 Label unvalidated detours and totals as estimates and propagate that uncertainty into plan confidence.
- [ ] 4.7 Add table-driven and property tests for range/reserve safety, unit conversion, rounding, fuel compatibility, detours, ties, and infeasible coverage.

## 5. Budgeted Map Providers and Cache

- [ ] 5.1 Define provider interfaces and metadata for geocoding, routing, station import, price import, and map tiles with runtime switches.
- [ ] 5.2 Make India Nominatim search user-triggered only, remove the U.S. restriction, enforce cross-worker request spacing below one request/second, identify the app, and cache results durably.
- [ ] 5.3 Implement the selected route provider with hard per-minute/daily safe budgets, timeout, bounded retry, circuit breaker, and attribution.
- [ ] 5.4 Reject unsupported waypoints/preferences explicitly and test provider capability negotiation.
- [x] 5.5 Version route-cache keys by the complete request, API, provider, station snapshot, observation watermark, and resolver policy.
- [ ] 5.6 Bound current cache TTL by quote expiry and implement explicit, labelled stale-cache fallback.
- [ ] 5.7 Add multi-worker budget/throttle, quota exhaustion, circuit opening/recovery, provider timeout, and cache invalidation tests.

## 6. India V2 API Contract

- [ ] 6.1 Add `/api/v2/route/` request validation for India locations, waypoints, vehicle, fuel/grade, preferences, maximum detour, strategy, and price-quality policy.
- [x] 6.2 Add India-only resolved-location checks and typed `unsupported_country`, provider, infeasible-route, and insufficient-price-data errors.
- [x] 6.3 Serialize route comparisons, selected plan, vehicle/assumptions, INR line items, detours, source attribution, quote traces, and data-quality summary.
- [ ] 6.4 Add paginated station search/detail endpoints exposing catalogue provenance and current price classes without leaking moderation data.
- [ ] 6.5 Add endpoint-specific request limits, payload limits, idempotency where required, and correlation identifiers.
- [x] 6.6 Update `openapi.yaml`, Postman examples, API version policy, and generated/handwritten contract tests.

## 7. Community Price Reporting

- [ ] 7.1 Add anonymous rotating contributor receipts and a report endpoint for station, fuel/grade, INR/litre, observed time, consent, and optional note.
- [ ] 7.2 Add network/device/contributor/station rate limits, duplicate suppression, identifier hashing/rotation, and retention cleanup.
- [ ] 7.3 Connect automated validation so rejected/quarantined reports cannot affect resolved quotes.
- [ ] 7.4 Add independent-contributor consensus and versioned reputation inputs without exposing contributor identity.
- [ ] 7.5 Add a least-privilege moderation interface for accept, reject, supersede, and retract actions with reason codes and immutable audit events.
- [ ] 7.6 Add receipt-based status/correction/removal flows and plain-language reporter feedback.
- [ ] 7.7 Add abuse, XSS, CSRF, authorization, quorum-evasion, retention, moderation-audit, correction, and immediate-retraction tests.

## 8. India Driver Experience

- [ ] 8.1 Replace the public U.S. route form and examples with India locations, petrol/diesel/grade, vehicle values, reserve, waypoints, preferences, strategy, and price-quality controls.
- [ ] 8.2 Add a local-first vehicle garage with validation, selection, export, and delete-all controls.
- [ ] 8.3 Build comparison and result views for INR/litre, kilometres, litres, route strategy, detour, reserve, source label/precision/as-of/confidence, and coverage warnings.
- [ ] 8.4 Build station detail and price-report flows with submission status, consent, correction receipt, and accessible validation errors.
- [ ] 8.5 Add versioned share links/payloads and local saved-plan JSON/GeoJSON with historical/stale re-open behaviour.
- [ ] 8.6 Add the PWA shell and explicit offline saved-plan view without prefetching third-party map tiles.
- [ ] 8.7 Add low-data mode with textual results first and optional lazy map/alternative details.
- [ ] 8.8 Externalize copy, add English-India formatting and Hindi-ready keys/fallbacks, then pass keyboard, screen-reader, focus, contrast, and responsive checks.
- [x] 8.9 Remove U.S. demos and U.S. runtime data from the public frontend; retain only isolated test fixtures until replacement tests no longer need them.

## 9. Security, Privacy, and Operations

- [ ] 9.1 Write the route-sharing/reporting threat model, privacy notice, retention schedule, source-attribution page, and incident/provider runbooks.
- [ ] 9.2 Enforce production secret/host/origin validation, HTTPS/security headers, least-privilege roles, safe text rendering, and log redaction.
- [ ] 9.3 Add structured metrics/logs for request outcomes, providers/budgets/circuits, cache, catalogue age, quote coverage, imports, reports, and moderation.
- [ ] 9.4 Configure a current zero-cost durable pilot deployment with technically enforced no-spend limits and document sleep, capacity, quota, and no-SLA constraints.
- [ ] 9.5 Add logical backups for canonical data and an automated isolated restore/integrity drill with recorded evidence.
- [ ] 9.6 Add coverage/status reporting that automatically marks pilot regions degraded or unsupported below data-quality thresholds.
- [ ] 9.7 Add dependency, secret, static security, migration, manifest, attribution, and container checks to CI.

## 10. End-to-End Verification and Release Gates

- [x] 10.1 Run backend unit/integration/contract suites and meet the agreed branch-coverage gate for every changed domain and failure path.
- [ ] 10.2 Run frontend lint, production build, component tests, browser flows, accessibility automation, and a manual keyboard/screen-reader checklist.
- [ ] 10.3 Verify deterministic replay from stored catalogue/observation/resolver versions and exact Decimal totals across repeated runs.
- [ ] 10.4 Load-test the selected pilot workload and verify latency, memory, database indexes, cache hit rate, hard provider budgets, and admission limits.
- [ ] 10.5 Run injected geocoder/router/price-import/cache/database failures and verify circuits, typed errors, no fabricated data, and recovery.
- [ ] 10.6 Run forward migration, backward-compatible rollback, bad-station-snapshot rollback, backup restore, and prior-artifact deployment drills.
- [ ] 10.7 Review every enabled data/provider registry entry and UI attribution against current official terms immediately before release.
- [ ] 10.8 Validate the OpenSpec change strictly and attach release evidence for specs, security, privacy, accessibility, performance, data rights, and operations.

## 11. Coverage-gated India Rollout

- [ ] 11.1 Deploy v2 privately with all unresolved official-price sources disabled and verify India-only behaviour and zero external billing risk.
- [ ] 11.2 Run community reporting in shadow mode, inspect false-positive, outlier, consensus, freshness, and moderation metrics, and tune versioned thresholds.
- [ ] 11.3 Enable validated community observations for one approved pilot region and publish its actual station/price coverage and service status.
- [ ] 11.4 Expand to another Indian region only after it independently passes station, price, provider, moderation, capacity, and restore gates.
- [ ] 11.5 Complete the v1 compatibility window, remove U.S. runtime routes/data, and verify rollback returns to an India version or maintenance mode only.
- [ ] 11.6 Record launch outcomes, unresolved limitations, free-tier capacity, and the concrete trigger for sponsorship, owned hosting, or a future budget.

## 12. Resumed Pilot Verification Checkpoints (2026-10-26)

Continue the existing 50–60 small-commit delivery plan from `docs/production-checkpoints.md`.
These checks use explicit fixtures and isolated databases; external data and launch gates remain separate.

- [x] 12.1 Finish the pending desktop/mobile production browser suite for price evidence, downloads, local vehicles, cancellation, errors, and optional maps.
- [ ] 12.2 Run the browser suite in CI and retain only failure diagnostics, without contacting public providers.
- [x] 12.3 Verify schema forward/backward migration and canonical-row preservation on SQLite and PostgreSQL.
- [ ] 12.4 Add and test a PostgreSQL restore drill that creates its own isolated database, compares canonical contents and migration state, and never restores into the configured source database.
- [ ] 12.5 Run the restore drill against a disposable PostgreSQL fixture and record integrity evidence without publishing private data.
- [ ] 12.6 Document provider/refresh failure response, source kill switches, quota recovery, and pilot admission gates.
- [ ] 12.7 Record current backend coverage, frontend checks, OpenSpec validation, delivery count, and remaining live-data/accessibility/deployment gates.
