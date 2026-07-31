# FuelUp India data-source registry

`data/source-registry.json` is the release gate for every external data or map
source. A source is not approved merely because its website is public or its API
is technically reachable.

Each entry records:

- the source owner and intended purpose;
- the official terms or policy URL reviewed;
- evidence supporting the permission status;
- the exact permitted use and required attribution;
- whether automated access and runtime use are enabled;
- a hard refresh/call budget; and
- the retention rule for downloaded or derived data.

Automated code must fail closed unless both `automated_access_allowed` and
`enabled` are true. `unresolved` and `blocked_until_terms_published` entries are
documentation, not authorization.

## Current safe baseline

- The Geofabrik India OpenStreetMap extract is approved for building a versioned
  station catalogue subject to ODbL and attribution.
- Public Nominatim is approved only for bounded, user-triggered submitted
  searches with global request spacing, identification, caching, attribution,
  and no autocomplete.
- Standard OSM tiles are approved only for attributed interactive viewing. The
  PWA must not prefetch or bulk-download them for offline use.
- PPAC and the oil marketing company sources remain disabled until automated
  reuse and redistribution permission is established.
- Public OSRM remains a development dependency until its operator policy and a
  safe production budget are recorded.
- Community reporting remains disabled until contribution terms, privacy,
  retention, validation, moderation, and abuse controls ship.

## Review procedure

1. Open the official owner-controlled terms and data documentation.
2. Record the review date and evidence without copying large copyrighted text.
3. State whether automation, caching, modification, and redistribution are
   permitted for FuelUp's intended use.
4. Record attribution and retention obligations.
5. Set a budget that cannot create charges or violate a public-service policy.
6. Enable the source only after tests prove the budget and kill switch.
7. Re-review before each public release and disable a source when terms change.

## Reproducible station extraction

Download the official India or zone `.osm.pbf` extract recorded in the source
registry, then run:

```bash
scripts/extract_osm_stations.sh western-zone-latest.osm.pbf india-fuel.geojson
python manage.py sync_source_registry
python manage.py import_osm_stations india-fuel.geojson \
  --snapshot-version western-zone-YYYY-MM-DD \
  --generated-at YYYY-MM-DDTHH:MM:SSZ \
  --market-code IN \
  --source-slug geofabrik-india-osm \
  --activate
```

The importer rejects non-fuel or invalid features, retains OSM source ids/tags,
computes quality metrics, imports idempotently by version/checksum, and activates
the snapshot atomically. Fuel availability is not inferred by default. For a
clearly labelled exploratory coverage report, `--infer-common-fuels` may add
petrol and diesel as inferred rows; production route recommendations must expose
or remove that uncertainty before launch.
