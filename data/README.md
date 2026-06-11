# Derived station data

`fuel-stations.csv` combines the exercise's `fuel-prices.csv` with approximate
city coordinates from the GeoNames U.S. postal-code dataset.

Regenerate it with:

```bash
python manage.py build_station_data
```

The command downloads `US.zip` from:
<https://download.geonames.org/export/zip/>

GeoNames data is licensed under Creative Commons Attribution 4.0:
<https://www.geonames.org/export/>

Coordinates represent a station's city/postal locality, not its exact street
entrance. The route optimizer therefore treats them as approximate candidate
locations and reports this limitation in the API response.
