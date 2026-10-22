# Provider and pilot operations

The repository is an engineering pilot. A passing test suite does not establish
provider rights, live India coverage, a free production entitlement, or public
readiness. API Mitra, HeiGIT, official price candidates, and community reporting
remain disabled in the checked-in source registry until their individual gates
are met. Credentials alone do not enable a source.

## Diagnose without spending provider quota

Run on the backend with its normal secret configuration:

```bash
.venv/bin/python manage.py provider_status
.venv/bin/python manage.py catalogue_report
```

`provider_status` reports key presence, registry state, configured monthly limits,
and recorded health without a network call or secret values. `catalogue_report`
requires an active catalogue and reports tag/geography completeness; it does not
establish price coverage or pump availability. The API offers `/api/v2/data-status/`
for aggregate catalogue, price scopes, and provider health, plus separate
`/api/health/live/` and `/api/health/ready/` endpoints. Readiness checks cache and
market data; it does not prove routing-provider entitlement or end-to-end routing.

For an incident, retain the release revision, UTC time, request correlation ID,
typed error code, and redacted provider status. Do not copy API keys, database
URLs, raw provider bodies, contributor tokens, or drivers' itineraries into logs
or public issues.

## Stop a source

The source registry is the runtime switch. To disable the price provider:

```bash
.venv/bin/python manage.py shell -c "from routes.models import SourceRegistry; print(SourceRegistry.objects.filter(slug='api-mitra-fuel').update(enabled=False))"
```

The count must be one for an existing source. Use the appropriate reviewed slug
for another provider. Disabling prevents new provider attempts. Disabled price
sources are excluded from quote resolution, and resolved-quote cache identity
prevents a warm plan from reusing their previous prices. Historical rows remain
available for audit; no row deletion or full-cache flush is needed.

`sync_source_registry` copies the checked-in registry into the database and can
overwrite an emergency runtime switch. Record the incident and reconcile the
registry before a later sync. Re-enable only after the permission, entitlement,
quota, provenance, and recovery review has been recorded.

## Price refresh and failure response

After a provider's review passes, configure its key, registry permissions and
minute/day/month limits, then schedule:

```bash
.venv/bin/python manage.py refresh_prices
```

A successful import within 24 hours skips another fetch. Snapshot checksums make
replayed imports idempotent; the import transaction leaves the previous valid
observations in place on validation failure. Overlapping schedulers can both
attempt a fetch, so run one scheduler and rely on shared hard quotas as the
final bound. The `--force` option bypasses cadence only; it cannot bypass quotas,
registry checks, or an open circuit.

Every attempted network request consumes a minute, UTC calendar-day, and UTC
calendar-month counter before I/O. Failed HTTP, timeout, transport, oversized,
and invalid responses remain charged. A later price-schema/import failure also
retains its transport charge. Zero or missing limits fail closed; the daily cap
is the smaller of configuration and the registry budget. Request failures are
never refunded by ingestion rollback.

| Symptom | Operator response |
| --- | --- |
| Missing key or disabled source | Check secret presence and the source's recorded review. Do not enable an unresolved source to clear an alert. |
| `provider_budget_exceeded` | Check the current UTC window and approved allowance. Wait for its next window; do not reset counters or raise a cap to make a request pass. |
| Repeated transport errors | Inspect the redacted health code and provider status. The shared circuit blocks calls after the configured threshold; wait for cooldown before one governed check. |
| Price-schema or geography failure | Keep the prior valid data, retain its original expiry, and quarantine the integration change. Transport success does not establish valid price data. |
| Missing or expired prices | Show unavailable/stale according to the request's policy. Narrow the pilot or pause recommendations; do not synthesize pump prices. |
| Invalid station import | Keep the prior valid catalogue. Rehearse snapshot recovery before activating another import. |
| Cache/database incident | Check dependency readiness, reduce admission, and follow the database recovery procedure. A live process alone is not ready for traffic. |

`provider_status --check-live routing` and `--check-live prices` deliberately
make governed calls and consume quota. Use them only after review and account
configuration, not in liveness probes or every route request. The automated
browser and backend regressions use explicit fixtures without public-provider
calls.

## Admit a private pilot

Keep public launch blocked until one candidate corridor has a reproducible
licensed station extract, measured geography/fuel completeness, permitted current
price samples, and a documented go/no-go decision. Record actual provider India
coverage, latency, free entitlement, billing controls, waypoint capabilities, and
failure behaviour. Review every enabled source's current terms and attribution.

Before admitting drivers, verify durable PostgreSQL and off-host backups, an
isolated restore, source switches, hard quota exhaustion, migration/application
rollback, privacy and moderation, accessible browser flows, and measured capacity.
See [database recovery](database-recovery.md) and the OpenSpec release gates.
The deployment manifests declare intended services; they do not provision a
durable free database or prove that a vendor currently offers a suitable free
plan. Publish observed coverage, capacity, sleep, and outage limits without an
SLA claim.
