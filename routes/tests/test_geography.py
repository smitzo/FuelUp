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
