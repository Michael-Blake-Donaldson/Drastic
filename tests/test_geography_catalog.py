from __future__ import annotations

import unittest

from reference_data.geography import (
    geography_csv_path,
    list_world_regions,
    reload_region_profiles,
    validate_geography_csv,
)


class GeographyCatalogTests(unittest.TestCase):
    def test_geography_csv_exists_and_validates(self) -> None:
        self.assertTrue(geography_csv_path().exists())
        self.assertEqual(validate_geography_csv(), [])

    def test_reload_region_profiles_returns_nonzero_count(self) -> None:
        count = reload_region_profiles()
        self.assertGreater(count, 0)
        self.assertGreater(len(list_world_regions()), 0)


if __name__ == "__main__":
    unittest.main()
