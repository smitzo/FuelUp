import csv
from decimal import Decimal
from functools import lru_cache

from django.conf import settings

from routes.domain.entities import Coordinate, Station


@lru_cache(maxsize=1)
def load_stations():
    path = settings.BASE_DIR / "data" / "fuel-stations.csv"
    stations = []
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            stations.append(
                Station(
                    opis_id=row["opis_id"],
                    name=row["name"],
                    address=row["address"],
                    city=row["city"],
                    state=row["state"],
                    retail_price=Decimal(row["retail_price"]),
                    coordinate=Coordinate(
                        latitude=float(row["latitude"]),
                        longitude=float(row["longitude"]),
                    ),
                )
            )
    return tuple(stations)
