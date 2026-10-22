# India pilot production checkpoints

Starting revision: `938b07d`. Requested delivery: 50–60 small, substantive commits.
Every checkpoint should have one reviewable purpose. No empty commits or history
rewrites; no automatic pushes. Existing source-capability edits were validated
and recorded independently before new work.

## Scope

- Provider configuration using `API_MITRA_API_KEY` and `HEIGIT_API_KEY`.
- Governed, budgeted price ingestion and routing with explicit provenance.
- Durable local/PostgreSQL deployment support, backups, and operational checks.
- A simpler road-guide interface; keep the truck scene and its animation.
- Appropriate backend, database, frontend, and browser verification.

The supplied names are not secret values. At initial inspection neither key nor
a cloud `DATABASE_URL` was configured. Live provider validation and public
readiness must remain distinct from mocked tests and local database checks.
The local PostgreSQL server is available for integration checks.

## Visual direction

Use the practical form-first organization of established route planners such as
[the AA](https://www.theaa.com/route-planner), with a printed road-guide feel:
warm white, charcoal, restrained rust, Georgia headings, and system sans-serif
body text. Use rules and spacing instead of gradients, glass, oversized pills,
and deep shadows. Preserve the truck artwork and movement. Keep mobile forms,
keyboard operation, reduced motion, and low-data use practical.

## Checkpoint groups

1. Research and source capability baseline.
2. Configuration, provider governance, provenance, geography, and quotas.
3. Budgeted HTTP transport, routing adapter, price parser, and refresh pipeline.
4. Data readiness, input protection, durable deployment, backup and recovery.
5. Catalogue coverage and import quality.
6. Typography, palette, layout, forms, loading, results, maps, and accessibility.
7. Useful local trip features and failure handling.
8. Automated and manual verification, runbooks, and final evidence.

The Git history is the authoritative checkpoint list. Finish with a delivery
record stating actual commit count, checks, runtime evidence, and remaining
external dependencies. Do not mark unchecked launch gates complete just because
supporting code exists.

## Delivery record

The batch from `938b07d` ends with 60 focused commits. The resumed verification
work starts after `a1b50be`; no pushes or deployment form part of this record.
See [verification and remaining gates](verification-2026-10-27.md) for the current
test counts, recovery evidence, source-control fixes, and next data-feasibility
work. The source registry still disables unresolved providers and public launch
remains gated by measured India station/price coverage and provider acceptance.
