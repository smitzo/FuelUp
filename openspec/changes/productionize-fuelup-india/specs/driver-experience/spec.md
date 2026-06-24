## ADDED Requirements

### Requirement: Local-first vehicle garage
The system SHALL let drivers create, edit, select, export, and delete vehicle
profiles locally without an account, and SHALL require explicit consent before
any later server sync.

#### Scenario: Returning driver selects a vehicle
- **WHEN** a driver has saved a valid vehicle profile in the browser
- **THEN** the route form can select it without sending the garage to the server before plan submission

#### Scenario: Driver deletes local data
- **WHEN** the driver chooses delete-all local data
- **THEN** saved vehicles, trips, and preferences are removed and the UI confirms completion

### Requirement: Saved and shareable plans
The system SHALL let a driver save plan JSON/GeoJSON locally and create a
versioned share representation that excludes private local metadata and clearly
retains price as-of and stale status.

#### Scenario: Shared plan is opened later
- **WHEN** a recipient opens a valid shared plan after one or more quotes expire
- **THEN** the original result is shown as historical/stale with an option to re-plan, not as a current quote

#### Scenario: Share payload excludes garage
- **WHEN** a driver shares one trip
- **THEN** unrelated saved vehicles, recent searches, contributor tokens, and local preferences are absent

### Requirement: PWA and honest offline behaviour
The system SHALL cache the application shell and explicitly saved plan data for
offline reading, SHALL show offline/stale state, and SHALL NOT prefetch or bulk
download map tiles from a provider that forbids it.

#### Scenario: Saved plan viewed offline
- **WHEN** the device is offline and a saved plan exists
- **THEN** route geometry, stops, assumptions, totals, source labels, and as-of time remain readable even if the basemap is unavailable

#### Scenario: New route requested offline
- **WHEN** an offline driver requests a new route
- **THEN** the UI explains that online providers are required and makes no false attempt to return a current plan

### Requirement: Low-data mode
The system SHALL provide a low-data mode that avoids nonessential provider calls,
automatic map work, and eager alternative detail while preserving the route
form and textual plan.

#### Scenario: Low-data route planning
- **WHEN** low-data mode is active and a route succeeds
- **THEN** the textual summary and stop list render before any optional map or alternative detail is fetched

### Requirement: Accessible route workflow
The system SHALL meet WCAG 2.2 AA acceptance checks for the route form, errors,
comparison, map alternative, stop list, report flow, dialogs, and loading states.

#### Scenario: Keyboard-only planning
- **WHEN** a driver uses only a keyboard
- **THEN** all inputs, validation, submission, strategy selection, stop details, save/share, and reporting actions are operable with visible focus

#### Scenario: Map information has a text equivalent
- **WHEN** a screen reader user receives a plan
- **THEN** route and stop information available on the map is also available in ordered semantic text

### Requirement: India-focused and localization-ready copy
The system SHALL use Indian examples and formats, externalized message keys,
locale-aware INR/number/date formatting, and a structure capable of English and
Hindi without concatenating translated fragments.

#### Scenario: English India formatting
- **WHEN** the active locale is English for India
- **THEN** INR, litres, kilometres, dates, and Indian place examples use the intended locale formats

#### Scenario: Missing Hindi translation
- **WHEN** a Hindi key is unavailable
- **THEN** the complete English fallback message appears without a broken mixed-language fragment

### Requirement: Price trust cues at decision points
The system SHALL show label, precision, source, as-of time, freshness, and
confidence wherever a price affects a recommended route or stop, with a short
plain-language explanation available.

#### Scenario: Estimated stop is recommended
- **WHEN** a recommended stop uses a city reference estimate
- **THEN** its card says estimated, identifies city-level precision, and does not visually imitate a reported station price

