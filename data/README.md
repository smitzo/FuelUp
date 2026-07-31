# Legacy exercise station fixture

`fuel-stations.csv` is retained only for compatibility tests around the
previous exercise API. It is not part of the market-configured v2 runtime and
must not be
displayed or described as current India station or price data.

Regenerate it with:

```bash
python manage.py build_station_data
```

The command downloads `US.zip` from:
<https://download.geonames.org/export/zip/>

GeoNames data is licensed under Creative Commons Attribution 4.0:
<https://www.geonames.org/export/>

Coordinates represent a station's city/postal locality, not its exact street
entrance. The legacy optimizer treats them as approximate candidates. V2
instead reads an active, market-scoped OSM station snapshot and append-only
price observations from the database; see [`../docs/data-sources.md`](../docs/data-sources.md).
