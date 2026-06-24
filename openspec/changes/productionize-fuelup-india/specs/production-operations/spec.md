## ADDED Requirements

### Requirement: Replaceable and budgeted providers
The system SHALL access geocoding, routing, station, price, and map services
through replaceable provider boundaries with configured timeout, concurrency,
rate and daily budgets, attribution, health state, and kill switch.

#### Scenario: Free quota is nearly exhausted
- **WHEN** the configured safe daily budget is reached
- **THEN** new provider calls stop before paid or prohibited usage and the system enters its documented degraded mode

#### Scenario: Provider is disabled
- **WHEN** an operator activates a provider kill switch
- **THEN** no new calls reach that provider without a code or client deployment

### Requirement: Public-service policy compliance
The system SHALL enforce Nominatim identification, caching, global request
spacing below its public limit, and no client autocomplete, and SHALL honour map
tile attribution, caching, and no-prefetch rules for the active provider.

#### Scenario: Concurrent geocodes arrive
- **WHEN** multiple application workers receive uncached location searches
- **THEN** their public Nominatim calls are serialized across the deployment and cached

#### Scenario: PWA installation occurs
- **WHEN** the service worker installs
- **THEN** it does not crawl, pre-seed, or bulk cache public OSM map tiles

### Requirement: Graceful provider failure
The system SHALL use bounded retries with jitter where safe, circuit breakers,
cached permitted data, typed errors, and no silent source substitution that
changes data meaning.

#### Scenario: Routing provider times out
- **WHEN** routing attempts exhaust their bounded timeout/retry policy
- **THEN** the circuit records the failure and the user receives a retryable provider error or a clearly stale cached plan

#### Scenario: Price importer fails
- **WHEN** a scheduled price import fails validation or transport
- **THEN** the previous valid data remains active, freshness continues aging, and an operator alert is emitted

### Requirement: Operational and data-quality observability
The system SHALL expose structured metrics/logs for request latency/errors,
cache hits, provider calls/budgets/circuits, active catalogue age, price label and
precision coverage, report states, and import results without logging secrets or
raw personal route histories.

#### Scenario: Coverage falls below gate
- **WHEN** fresh usable price or station coverage drops below a configured pilot-region threshold
- **THEN** the region is marked degraded/unsupported and operators receive an actionable signal

#### Scenario: Request is traced
- **WHEN** a route request crosses frontend, API, providers, and resolver
- **THEN** a correlation identifier links allowed logs without recording a full personal itinerary in general logs

### Requirement: Durable data and tested restore
The system SHALL keep community observations, moderation events, source
registry, and active snapshot metadata in durable storage, run logical backups
on a documented schedule, and prove restore in an isolated environment.

#### Scenario: Restore drill
- **WHEN** the release restore drill uses the latest backup
- **THEN** schema, observations, moderation history, source registry, and active snapshot are restored and integrity checks pass

#### Scenario: Ephemeral web instance restarts
- **WHEN** an application container loses its local filesystem
- **THEN** canonical community and moderation data remains available from durable storage

### Requirement: Security and privacy baseline
The system SHALL apply secure headers and transport, server-side validation,
least-privilege administration, CSRF/authentication controls as applicable,
secret separation, dependency scanning, retention rules, data export/deletion
flows, and a documented threat model for reporting and sharing.

#### Scenario: Secret is absent in production
- **WHEN** a required production secret or safe host/origin setting is missing
- **THEN** startup fails closed with no secret value printed

#### Scenario: Malicious report note is displayed
- **WHEN** a report note contains executable markup
- **THEN** clients render it as inert text and no script executes

### Requirement: Versioned migration and rollback
The system SHALL introduce India v2 alongside a bounded compatibility window,
version schema and API changes, retain the previous station snapshot, and
support rollback without publicly restoring the U.S. product.

#### Scenario: India cutover succeeds
- **WHEN** v2 data, API, frontend, and release gates pass
- **THEN** the public product accepts India routes only and no U.S. demo or U.S. runtime dataset is shown

#### Scenario: New release is rolled back
- **WHEN** the India release fails a post-deploy gate
- **THEN** the prior India artifact/snapshot or maintenance mode is restored while append-only reports remain intact

### Requirement: Release evidence gates
The system SHALL block public pilot release until automated tests, data-source
permission review, attribution, migrations, API contract, deterministic math,
provider failures/budgets, security, accessibility, performance, backup restore,
and rollback checks have recorded evidence.

#### Scenario: Data rights are unresolved
- **WHEN** a candidate automated price source lacks reuse evidence
- **THEN** the release can proceed only with that source disabled and no claims based on it

#### Scenario: All pilot gates pass
- **WHEN** every required check has current passing evidence for the release artifact
- **THEN** the operator may enable the coverage-gated public pilot

### Requirement: Honest zero-cost service boundary
The system SHALL publish actual service status and data coverage and SHALL not
promise unlimited capacity, paid-provider equivalence, or an SLA that the
zero-cost deployment cannot support.

#### Scenario: Capacity budget is exhausted
- **WHEN** the free deployment reaches a safe capacity limit
- **THEN** admission/rate limits protect existing users and explain the temporary limit without incurring charges
