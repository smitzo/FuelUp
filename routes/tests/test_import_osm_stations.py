import json
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from routes.models import FuelStation, StationFuel, StationSnapshot


class ImportOsmStationsTests(TestCase):
    def setUp(self):
        call_command("sync_source_registry", verbosity=0)
        self.payload = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {
                        "@id": "node/100",
                        "amenity": "fuel",
                        "name": "Ahmedabad Fuel",
                        "brand": "Test OMC",
                        "addr:city": "Ahmedabad",
                        "addr:state": "Gujarat",
                        "fuel:octane_91": "yes",
                        "fuel:diesel": "yes",
                    },
                    "geometry": {
                        "type": "Point",
                        "coordinates": [72.5714, 23.0225],
                    },
                },
                {
                    "type": "Feature",
                    "properties": {
                        "@id": "way/200",
                        "amenity": "fuel",
                        "name": "Vadodara Fuel",
                        "addr:city": "Vadodara",
                        "addr:state": "Gujarat",
                    },
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [
                                [73.1800, 22.3000],
                                [73.1810, 22.3000],
                                [73.1810, 22.3010],
                                [73.1800, 22.3000],
                            ]
                        ],
                    },
                },
                {
                    "type": "Feature",
                    "properties": {"@id": "node/300", "amenity": "cafe"},
                    "geometry": {
                        "type": "Point",
                        "coordinates": [72.6, 23.1],
                    },
                },
            ],
        }

    def test_imports_idempotent_snapshot_with_quality_metrics(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "market-fuel.geojson"
            path.write_text(json.dumps(self.payload), encoding="utf-8")
            output = StringIO()

            call_command(
                "import_osm_stations",
                str(path),
                snapshot_version="western-zone-test-v1",
                generated_at="2026-08-09T20:21:21Z",
                activate=True,
                infer_common_fuels=True,
                stdout=output,
            )
            call_command(
                "import_osm_stations",
                str(path),
                snapshot_version="western-zone-test-v1",
                generated_at="2026-08-09T20:21:21Z",
                activate=True,
                infer_common_fuels=True,
                stdout=output,
            )

        snapshot = StationSnapshot.objects.get(version="western-zone-test-v1")
        self.assertTrue(snapshot.is_active)
        self.assertEqual(snapshot.quality_metrics["station_count"], 2)
        self.assertEqual(snapshot.quality_metrics["invalid_feature_count"], 1)
        self.assertEqual(FuelStation.objects.count(), 2)
        self.assertEqual(StationFuel.objects.count(), 4)
        self.assertEqual(
            StationFuel.objects.filter(is_inferred=True).count(),
            2,
        )
        self.assertIn("already imported", output.getvalue())

    def test_same_version_with_changed_content_fails(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "market-fuel.geojson"
            path.write_text(json.dumps(self.payload), encoding="utf-8")
            arguments = (
                "import_osm_stations",
                str(path),
            )
            options = {
                "snapshot_version": "western-zone-test-v1",
                "generated_at": "2026-08-09T20:21:21Z",
            }
            call_command(*arguments, **options)
            self.payload["features"][0]["properties"]["name"] = "Changed"
            path.write_text(json.dumps(self.payload), encoding="utf-8")

            with self.assertRaisesRegex(CommandError, "another checksum"):
                call_command(*arguments, **options)
