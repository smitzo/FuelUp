# India pilot verification record — 2026-10-27

This completes the 50–60-commit engineering batch recorded in
[production checkpoints](production-checkpoints.md): 60 focused commits after
`938b07d`, including 11 resumed checkpoints after `a1b50be`. Runtime fixes and
runbooks end at `655ca57`; the final checkpoint records this evidence, updates
README verification commands, and reconciles OpenSpec tasks. Git history is the
authoritative revision list.

## Implemented and verified

- Desktop/mobile contract browser checks cover price evidence, downloads,
  local vehicle validation/save/restore/delete, cancellation, useful coverage
  errors, optional maps, results focus, and keyboard skip navigation. The truck
  remains present during loading. External requests are blocked in the suite.
- Forward → backward → forward migrations preserve station identity, fuel data,
  price observations, import provenance, moderation history, contribution
  receipts, and the observation watermark on both supported databases.
- A new `verify_database_restore` management command creates a private backup
  from an exported read-only PostgreSQL snapshot, restores only into its own
  randomly named database, compares canonical rows/migration history/constraints,
  and removes temporary artifacts. Backup and restore have five-minute bounds.
- Real local PostgreSQL restore checks cover normal recovery, a source write
  during backup, injected restore failure, and deliberately corrupted restored
  prices. Failure tests verify cleanup and an unchanged source database. All
  records are explicit synthetic test data.
- Scheduled price refresh no longer wraps provider accounting in its import
  transaction. Failed requests keep their quota charges and circuit failures;
  repeated network failures stop at the configured circuit threshold. A valid
  transport with invalid price data also remains charged.
- Plan cache identity now includes resolved quote evidence. Disabling a source,
  losing a quote, or changing freshness cannot reuse a previous current plan
  merely because the observation watermark stayed unchanged. Cache contention,
  bounded waiting, unavailable lock storage, and lock ownership have regressions.
- CI is configured for both databases, matching PostgreSQL 18 backup tools, and
  production browser flows with short-lived failure diagnostics. The workflow
  was parsed and checked locally; hosted CI awaits a requested push.

## Verification results

| Check | Recorded result |
| --- | --- |
| `.venv/bin/python -m coverage run manage.py test --noinput` against local PostgreSQL | 164 tests; all pass; 20.729 seconds. Includes actual migration and isolated restore operations. |
| Full suite with a disposable SQLite configuration | 164 tests; pass with 4 PostgreSQL-only restore tests skipped; 16.235 seconds. |
| `.venv/bin/python -m coverage report` | 89% combined statement/branch coverage; required repository threshold is 80%. |
| Changed runtime modules | Plan cache 99%; backup 95%; isolated restore 94%. |
| `npm run test:browser` with local Chrome and a production build | 8 pass: 4 desktop and 4 mobile; 6.9 seconds. Synthetic contracts, no live provider evidence. |
| `npm run lint`, `npm run typecheck`, `npm run build` | Pass. |
| `.venv/bin/python -m ruff check fuelup routes scripts manage.py gunicorn.conf.py` | Pass. |
| Django system check and production `check --deploy` with a synthetic CI secret | Pass; no identified issues. |
| `makemigrations --check --dry-run` | No model changes detected. The sandbox blocked this command's optional source-database history lookup; actual migration paths passed in the PostgreSQL and SQLite test databases. |
| `scripts/validate_manifests.py` and CI YAML parse | Pass. |
| `openspec validate --all --strict --no-interactive` | Pass for `productionize-fuelup-india`. |
| `git diff --check` | Pass. |

A repeated frontend build briefly failed while parsing TypeScript's
`--showConfig` output. Direct configuration JSON validation and the subsequent
standalone production build passed. No TypeScript checks were disabled.

## Remaining launch gates and next steps

The engineering checks do not establish live nationwide prices, permitted free
provider access, a deployed durable database, corridor coverage, full WCAG
acceptance, load capacity, or public readiness. No source was enabled for these
tests. The existing unresolved provider and official-price kill switches remain.

Continue at OpenSpec tasks **1.4–1.8**: run the reproducible OSM extraction on a
real India/zone PBF, publish corridor/tag/duplicate coverage, collect permitted
dated price samples, validate actual provider entitlement and India behaviour,
and record the pilot go/no-go decision. The current importer and quality-report
commands support that investigation; synthetic recovery fixtures do not satisfy
it.

After that gate, finish the selected-stop driving-detour validation, full
community reporting/moderation/privacy flows, saved-plan reopening/PWA,
localization, automated and manual accessibility, load/failure exercises,
retained off-host backup recovery, and deployment/application rollback evidence.
Broader OpenSpec release tasks remain unchecked where these parts are incomplete.
