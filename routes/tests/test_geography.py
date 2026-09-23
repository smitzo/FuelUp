from collections import defaultdict
from types import SimpleNamespace

from django.test import SimpleTestCase

from routes.domain.geography import geographic_slug, scoped_geography_id


class GeographyTests(SimpleTestCase):
    def test_city_aliases_and_whitespace(self):
        self.assertEqual(scoped_geography_id(" IN ", "Karnataka", "Bangalore"),
                         "in/karnataka/bengaluru")
        self.assertEqual(geographic_slug("  West  Bengal "), "west-bengal")

    def test_equal_city_names_in_different_states_do_not_collide(self):
        self.assertNotEqual(scoped_geography_id("in", "Bihar", "Rampur"),
                            scoped_geography_id("in", "Uttar Pradesh", "Rampur"))

    def test_missing_parent_and_oversized_ids_are_rejected(self):
        with self.assertRaises(ValueError):
            scoped_geography_id("in", locality="Ahmedabad")
        with self.assertRaises(ValueError):
            scoped_geography_id("in", "x" * 161)


class ReferenceScopeTests(SimpleTestCase):
    def test_aggregator_reference_requires_scoped_parent(self):
        from routes.domain.fuel_data import SourceType
        from routes.infrastructure.observation_queries import (
            applicable_reference_values,
        )
        station = SimpleNamespace(city="Bangalore", district="", state="Karnataka")
        references = defaultdict(list)
        references["city"] = [
            SimpleNamespace(geography_id=value,
                            source_type=SourceType.THIRD_PARTY_REFERENCE)
            for value in ("Bangalore", "in/karnataka/bengaluru", "in/bihar/bengaluru")
        ]
        market = SimpleNamespace(country_code="in", country_geography_id="india")
        result = applicable_reference_values(station, references, market)
        self.assertEqual([item.geography_id for item in result],
                         ["in/karnataka/bengaluru"])
