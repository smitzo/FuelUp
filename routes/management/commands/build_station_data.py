import csv
import io
import unicodedata
import urllib.request
import zipfile
from collections import defaultdict
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

GEONAMES_US_URL = "https://download.geonames.org/export/zip/US.zip"
US_STATE_CODES = {
    "AL",
    "AK",
    "AZ",
    "AR",
    "CA",
    "CO",
    "CT",
    "DE",
    "FL",
    "GA",
    "HI",
    "ID",
    "IL",
    "IN",
    "IA",
    "KS",
    "KY",
    "LA",
    "ME",
    "MD",
    "MA",
    "MI",
    "MN",
    "MS",
    "MO",
    "MT",
    "NE",
    "NV",
    "NH",
    "NJ",
    "NM",
    "NY",
    "NC",
    "ND",
    "OH",
    "OK",
    "OR",
    "PA",
    "RI",
    "SC",
    "SD",
    "TN",
    "TX",
    "UT",
    "VT",
    "VA",
    "WA",
    "WV",
    "WI",
    "WY",
    "DC",
}


def normalize(value):
    text = (
        unicodedata.normalize("NFKD", value.strip())
        .encode("ascii", "ignore")
        .decode()
    )
    return " ".join(text.casefold().replace("-", " ").split())


class Command(BaseCommand):
    help = "Enrich the supplied station CSV with approximate city coordinates."

    def add_arguments(self, parser):
        parser.add_argument(
            "--geonames-zip",
            type=Path,
            help="Use an already-downloaded GeoNames US.zip file.",
        )
        parser.add_argument(
            "--output",
            type=Path,
            default=settings.BASE_DIR / "data" / "fuel-stations.csv",
        )

    def handle(self, *args, **options):
        source = settings.BASE_DIR / "fuel-prices.csv"
        if not source.exists():
            raise CommandError(f"Missing source file: {source}")

        archive = options["geonames_zip"]
        archive_bytes = archive.read_bytes() if archive else self._download()
        places = self._load_places(archive_bytes)
        rows, unmatched = self._enrich(source, places)

        output = options["output"]
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)

        self.stdout.write(
            self.style.SUCCESS(
                f"Wrote {len(rows)} U.S. stations to {output}; "
                f"{unmatched} rows had no city match and were omitted."
            )
        )

    def _download(self):
        request = urllib.request.Request(
            GEONAMES_US_URL,
            headers={"User-Agent": settings.EXTERNAL_API_USER_AGENT},
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.read()
        except OSError as exc:
            raise CommandError(f"Could not download GeoNames data: {exc}") from exc

    @staticmethod
    def _load_places(archive_bytes):
        places = defaultdict(list)
        with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
            data_name = next(
                name for name in archive.namelist() if Path(name).name == "US.txt"
            )
            with archive.open(data_name) as raw:
                rows = csv.reader(
                    io.TextIOWrapper(raw, encoding="utf-8"),
                    delimiter="\t",
                )
                for row in rows:
                    state = row[4]
                    if state not in US_STATE_CODES:
                        continue
                    point = (float(row[9]), float(row[10]))
                    places[(normalize(row[2]), state)].append(point)

        result = {}
        for key, points in places.items():
            result[key] = (
                sum(point[0] for point in points) / len(points),
                sum(point[1] for point in points) / len(points),
            )
        return result

    @staticmethod
    def _enrich(source, places):
        enriched = []
        unmatched = 0
        with source.open(newline="", encoding="utf-8-sig") as handle:
            for row in csv.DictReader(handle):
                state = row["State"].strip()
                if state not in US_STATE_CODES:
                    continue
                key = (normalize(row["City"]), state)
                point = places.get(key)
                if point is None:
                    point = BuildStationDataFallback.find(key, places)
                if point is None:
                    unmatched += 1
                    continue
                enriched.append(
                    {
                        "opis_id": row["OPIS Truckstop ID"].strip(),
                        "name": row["Truckstop Name"].strip(),
                        "address": row["Address"].strip(),
                        "city": row["City"].strip(),
                        "state": state,
                        "retail_price": row["Retail Price"].strip(),
                        "latitude": f"{point[0]:.6f}",
                        "longitude": f"{point[1]:.6f}",
                    }
                )
        return enriched, unmatched


class BuildStationDataFallback:
    @staticmethod
    def find(key, places):
        city, state = key
        compact = city.replace(" ", "")
        matches = [
            point
            for place_key, point in places.items()
            if isinstance(place_key, tuple) and place_key[1] == state
            and place_key[0].replace(" ", "") == compact
        ]
        return matches[0] if matches else None
