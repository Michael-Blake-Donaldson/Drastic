from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from reference_data.geography import (
    geography_csv_path,
    geography_csv_schema_help_text,
    list_world_regions,
    REQUIRED_COLUMNS,
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

    def test_validate_geography_csv_reports_missing_columns(self) -> None:
        with TemporaryDirectory() as temp_dir:
            csv_path = Path(temp_dir) / "invalid.csv"
            csv_path.write_text("world_region,country\nEurope,France\n", encoding="utf-8")
            errors = validate_geography_csv(csv_path)
            self.assertTrue(errors)
            self.assertIn("Missing required columns", errors[0])

    def test_validate_geography_csv_accepts_valid_minimal_file(self) -> None:
        with TemporaryDirectory() as temp_dir:
            csv_path = Path(temp_dir) / "valid.csv"
            csv_path.write_text(
                "\n".join(
                    [
                        "world_region,country,region,latitude,longitude,infrastructure_damage_percent,road_access_score,health_operability_score,local_water_liters_per_day,local_food_supply_ratio",
                        "Europe,France,Ile-de-France,48.8566,2.3522,20,0.86,0.88,30000,0.39",
                    ]
                ),
                encoding="utf-8",
            )
            self.assertEqual(validate_geography_csv(csv_path), [])

    def test_schema_help_text_includes_columns_and_example(self) -> None:
        help_text = geography_csv_schema_help_text()
        self.assertIn("Required header columns", help_text)
        self.assertIn("Example row", help_text)
        for column in REQUIRED_COLUMNS:
            self.assertIn(column, help_text)


if __name__ == "__main__":
    unittest.main()
