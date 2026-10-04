from django.test import SimpleTestCase
from django.utils import timezone

from routes.management.commands.import_osm_stations import _normalize_feature


class OsmIdentityTests(SimpleTestCase):
    def test_numeric_ids_keep_node_way_namespace(self):
        ids = []
        for kind in ("node", "way", "relation"):
            feature = {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [72.5, 23]},
                "properties": {
                    "@type": kind,
                    "@id": 123,
                    "amenity": "fuel",
                    "fuel:diesel": "yes",
                },
            }
            station, _ = _normalize_feature(feature, False, timezone.now())
            ids.append(station["stable_id"])
        self.assertEqual(len(set(ids)), 3)
