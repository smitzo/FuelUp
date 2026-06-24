## ADDED Requirements

### Requirement: Minimal price report submission
The system SHALL accept a report containing station, fuel type/grade, INR/litre
price, observation time, and consent to the contribution terms, with an optional
text note and no required photo.

#### Scenario: Valid anonymous report
- **WHEN** a driver submits a valid recent observation for an active station
- **THEN** the system records it under a rotating pseudonymous contributor identifier and returns its validation state

#### Scenario: Future observation is rejected
- **WHEN** the submitted observation time is beyond the allowed clock-skew window
- **THEN** the report is rejected with a field-level error

### Requirement: Automated plausibility and duplicate checks
The system SHALL validate ranges, fuel compatibility, duplicate submissions,
change velocity, geographic applicability, and deviation from recent reference
or consensus before accepting a report into quote resolution.

#### Scenario: Exact duplicate report
- **WHEN** the same pseudonymous contributor repeats an equivalent station price inside the duplicate window
- **THEN** the second submission is recorded or counted as a duplicate but does not independently raise confidence

#### Scenario: Extreme value needs review
- **WHEN** a report exceeds configured absolute or percentage deviation thresholds
- **THEN** it is quarantined for moderation and cannot influence a resolved quote

### Requirement: Abuse controls with data minimization
The system SHALL apply per-network, device-token, contributor, and station rate
limits while retaining no raw abuse identifier longer than the documented
security purpose requires.

#### Scenario: Submission rate exceeded
- **WHEN** a reporter exceeds an applicable limit
- **THEN** the API returns `429` with retry guidance and stores no additional price observation

#### Scenario: Privacy retention elapses
- **WHEN** the retention period for raw network security data expires
- **THEN** the raw value is deleted or irreversibly transformed while the price observation remains auditable

### Requirement: Consensus and contributor reputation
The system SHALL calculate confidence from independent agreement, freshness,
source precision, and contributor history without exposing contributor identity
or letting one contributor simulate quorum.

#### Scenario: Independent agreement increases confidence
- **WHEN** independent contributors submit compatible fresh station observations
- **THEN** quote confidence increases according to the versioned policy and contributing report ids are recorded

#### Scenario: Same actor uses multiple sessions
- **WHEN** abuse signals link nominally separate reports to one actor
- **THEN** those reports count as one contributor for consensus and may be quarantined

### Requirement: Moderation and immutable audit trail
The system SHALL allow authorized moderators to accept, reject, supersede, or
retract reports with reason codes, and SHALL retain actor, time, prior state, and
new state in an immutable audit event.

#### Scenario: Accepted report is retracted
- **WHEN** a moderator confirms that an accepted report was false
- **THEN** it stops influencing new quotes immediately and the retraction reason remains auditable

#### Scenario: Unauthorized moderation attempt
- **WHEN** a non-moderator calls a moderation action
- **THEN** the system denies it, records a security event, and leaves report state unchanged

### Requirement: Reporter feedback and correction
The system SHALL return understandable submission status and SHALL provide a
privacy-preserving method to correct or request removal of a contributor's own
report where legally or operationally required.

#### Scenario: Report is pending
- **WHEN** automated checks cannot safely accept a plausible report
- **THEN** the contributor sees `pending review` and the report does not yet influence plans

#### Scenario: Contributor corrects a mistake
- **WHEN** a contributor with the report receipt submits a valid correction
- **THEN** a linked superseding observation is created without rewriting the original

