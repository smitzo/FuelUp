## ADDED Requirements

### Requirement: Versioned India station catalogue
The system SHALL import an India station catalogue reproducibly, assign stable
station identities, retain source identifiers and attribution, record snapshot
time and coordinate precision, and activate a snapshot atomically.

#### Scenario: Idempotent station import
- **WHEN** the same source snapshot is imported twice
- **THEN** both runs produce the same active station records, version, and quality counts without duplicates

#### Scenario: Bad snapshot is rolled back
- **WHEN** a new snapshot fails coverage or schema gates after import
- **THEN** the previous catalogue remains active and the failed snapshot is not used for planning

### Requirement: Append-only price observations
The system SHALL store price observations independently from stations with fuel
type/grade, INR/litre value, source, geographic precision, observed/effective,
received and expiry times, validation state, and provenance.

#### Scenario: City reference remains city precision
- **WHEN** an official city price is ingested and used near a station
- **THEN** its observation remains city-level and is never stored or presented as a station observation

#### Scenario: Correction preserves history
- **WHEN** an accepted observation is later corrected or retracted
- **THEN** the original row remains auditable and a state/event records the correction

### Requirement: Honest price labels
The system SHALL label every displayed price as `reported`, `reference`,
`estimated`, `stale`, or `unavailable`, with source and as-of time. It SHALL use
`live` only for a permitted, current, station-level feed whose source contract
supports that meaning.

#### Scenario: Community report is not called official or live
- **WHEN** a fresh community station report is selected
- **THEN** the UI labels it `reported` and shows its observation time and confidence

#### Scenario: No usable value exists
- **WHEN** no valid observation or permitted estimate applies
- **THEN** the station price is `unavailable` and no fabricated numeric value is shown

### Requirement: Deterministic price resolution
The system SHALL resolve a quote using a versioned policy that filters invalid or
expired data, prefers station precision and corroboration, and records every
contributing observation identifier.

#### Scenario: Community consensus beats one outlier
- **WHEN** two independent fresh reports agree within tolerance and a third report is an outlier
- **THEN** the resolver selects the consensus value and excludes the outlier with a recorded reason

#### Scenario: Resolution can be reproduced
- **WHEN** a stored catalogue version, observation watermark, resolver version, and evaluation time are replayed
- **THEN** the same resolved quotes and labels are produced

### Requirement: Configurable freshness and stale behaviour
The system SHALL apply source-specific freshness windows and SHALL never present
an expired observation as current. Stale data may influence only an explicitly
stale estimate allowed by the request policy.

#### Scenario: Daily reference expires
- **WHEN** an official daily reference is older than its configured freshness window
- **THEN** its current-reference eligibility ends and any fallback use is marked stale

#### Scenario: Strict quality policy rejects fallback
- **WHEN** the driver requires station-reported prices and all applicable reports are expired
- **THEN** the plan returns `insufficient_price_data` rather than using a city estimate

### Requirement: Plan-level data quality summary
The system SHALL report catalogue age, price as-of time, precision/label mix,
confidence, unresolved stops, and the estimated spend percentage attributable
to each price class.

#### Scenario: Mixed-quality plan
- **WHEN** a plan uses both station reports and city reference estimates
- **THEN** the response and UI disclose both classes and their shares of estimated spend

### Requirement: Source permission registry
The system SHALL block automated ingestion from any source without an enabled
registry entry recording ownership, terms or permission evidence, allowed use,
attribution, refresh budget, and kill switch.

#### Scenario: Undocumented endpoint is configured
- **WHEN** an operator attempts to enable a source with no recorded automated-use permission
- **THEN** ingestion fails closed before any source request is made

#### Scenario: Source permission is withdrawn
- **WHEN** a source registry entry is disabled
- **THEN** new fetches stop immediately while historical provenance and permitted retained data remain auditable

### Requirement: Data-aware route cache
The system SHALL include vehicle/preferences, API version, station snapshot,
observation watermark, and resolver version in route-cache identity, and SHALL
not keep a current result beyond its earliest quote expiry.

#### Scenario: Price data changes
- **WHEN** an accepted observation changes the active watermark for a cached route
- **THEN** a subsequent matching request does not return the older plan as current

#### Scenario: Degraded stale cache is served
- **WHEN** providers fail and policy allows a stale cached plan
- **THEN** the response includes `stale=true`, the original as-of time, and a prominent warning

