## ADDED Requirements

### Requirement: India-only trip locations
The system SHALL accept and resolve public trip locations only within India and
SHALL reject resolved locations outside India with a typed validation error.

#### Scenario: Indian locations are accepted
- **WHEN** a driver submits an origin and destination that resolve inside India
- **THEN** the system plans the trip using the India product contract

#### Scenario: Foreign location is rejected
- **WHEN** either resolved endpoint is outside India
- **THEN** the system returns `unsupported_country` without creating a route plan

### Requirement: Configurable vehicle profile
The system SHALL require a vehicle profile containing fuel type, tank capacity
in litres, efficiency in kilometres per litre, starting fuel, and reserve fuel,
and SHALL validate physically consistent bounds.

#### Scenario: Real vehicle values drive the plan
- **WHEN** a driver submits a valid 35-litre petrol vehicle at 18 km/litre with 8 litres starting fuel and 3 litres reserve
- **THEN** range, purchases, and cost are calculated from those values rather than legacy constants

#### Scenario: Impossible profile is rejected
- **WHEN** starting fuel plus reserve exceeds tank capacity or any required value is non-positive
- **THEN** the API returns field-level validation errors and does not call a map provider

### Requirement: Indian units and monetary precision
The system SHALL expose public distance in kilometres, volume in litres,
efficiency in kilometres per litre, and money in INR, and SHALL use decimal
arithmetic with an explicit rounding rule for prices and totals.

#### Scenario: Plan uses Indian units
- **WHEN** a route plan succeeds
- **THEN** every distance, fuel, efficiency, unit price, subtotal, and total is labelled in the Indian contract units

#### Scenario: Cost is reproducible
- **WHEN** the same versioned route, quotes, vehicle, and preferences are evaluated twice
- **THEN** line-item and total INR values are byte-for-byte equivalent after serialization

### Requirement: Fuel-compatible and range-safe stops
The system SHALL select only stations that serve the requested fuel and grade,
SHALL preserve the requested reserve at all planned points, and SHALL reject a
plan containing an unreachable leg.

#### Scenario: Diesel vehicle excludes petrol-only station
- **WHEN** a cheaper petrol-only station lies on a diesel vehicle route
- **THEN** that station is not a candidate for the diesel fuel plan

#### Scenario: Reserve makes a leg infeasible
- **WHEN** a leg can be reached only by consuming the configured reserve
- **THEN** the route alternative is marked infeasible rather than spending the reserve

### Requirement: Waypoints and bounded route preferences
The system SHALL support ordered waypoints, maximum station detour, and only
those toll/highway preferences confirmed by the active routing provider. It
SHALL disclose when a requested preference cannot be honoured.

#### Scenario: Ordered waypoint trip
- **WHEN** a driver plans Pune to Bengaluru via Kolhapur
- **THEN** the returned route visits Kolhapur in the requested order and optimizes fuel over the complete journey

#### Scenario: Unsupported preference
- **WHEN** a driver requests toll avoidance from a provider that cannot enforce it
- **THEN** the system rejects or explicitly marks the preference unsupported rather than silently ignoring it

### Requirement: Route strategy comparison
The system SHALL return comparable cheapest-estimated, fastest, and balanced
route summaries when sufficient alternatives and data exist, using one
documented scoring policy per strategy.

#### Scenario: Alternatives can be compared
- **WHEN** at least two feasible route alternatives have adequate price coverage
- **THEN** the response shows distance, duration, fuel cost, stops, detour estimate, data confidence, and selection reason for each strategy

#### Scenario: Cheapest claim is not justified
- **WHEN** price coverage is below the configured cheapest-claim threshold
- **THEN** the UI uses `lowest estimated cost` and displays the coverage limitation instead of `cheapest`

### Requirement: Selected-stop detour handling
The system SHALL include selected-station detour distance and fuel in totals when
the route can be waypoint-validated, and SHALL label detours as estimated when
validation cannot run within the provider budget.

#### Scenario: Waypoint validation succeeds
- **WHEN** the provider validates the selected stops within the routing-call budget
- **THEN** route distance, duration, fuel consumption, and totals use the validated stop geometry

#### Scenario: Validation is unavailable
- **WHEN** provider capability or quota prevents waypoint validation
- **THEN** the plan remains usable only with an explicit estimated-detour label and confidence impact

