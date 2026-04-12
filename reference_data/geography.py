from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RegionProfile:
    world_region: str
    country: str
    region: str
    latitude: float
    longitude: float
    infrastructure_damage_percent: float
    road_access_score: float
    health_operability_score: float
    local_water_liters_per_day: float
    local_food_supply_ratio: float


REQUIRED_COLUMNS: tuple[str, ...] = (
    "world_region",
    "country",
    "region",
    "latitude",
    "longitude",
    "infrastructure_damage_percent",
    "road_access_score",
    "health_operability_score",
    "local_water_liters_per_day",
    "local_food_supply_ratio",
)

SAMPLE_ROW: tuple[str, ...] = (
    "Europe",
    "France",
    "Ile-de-France",
    "48.8566",
    "2.3522",
    "24.0",
    "0.83",
    "0.88",
    "30000",
    "0.39",
)


def geography_csv_path() -> Path:
    return Path(__file__).with_name("geography_profiles.csv")


def validate_geography_csv(csv_path: Path | None = None) -> list[str]:
    path = csv_path or geography_csv_path()
    if not path.exists():
        return [f"Missing geography CSV file: {path}"]

    errors: list[str] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            return ["Geography CSV is empty or missing a header row."]

        missing_columns = [column for column in REQUIRED_COLUMNS if column not in reader.fieldnames]
        if missing_columns:
            errors.append(
                "Missing required columns: " + ", ".join(missing_columns)
            )
            return errors

        for line_number, row in enumerate(reader, start=2):
            for column in ("world_region", "country", "region"):
                if not (row.get(column) or "").strip():
                    errors.append(f"Line {line_number}: '{column}' cannot be empty.")

            for numeric_column in REQUIRED_COLUMNS[3:]:
                value = (row.get(numeric_column) or "").strip()
                try:
                    float(value)
                except ValueError:
                    errors.append(
                        f"Line {line_number}: '{numeric_column}' must be numeric (got '{value}')."
                    )

    return errors


def preview_geography_csv(csv_path: Path, max_rows: int = 10) -> dict[str, object]:
    sample_rows: list[str] = []
    world_regions: set[str] = set()
    countries: set[str] = set()
    total_rows = 0

    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            world_region = (row.get("world_region") or "").strip()
            country = (row.get("country") or "").strip()
            region = (row.get("region") or "").strip()
            latitude = (row.get("latitude") or "").strip()
            longitude = (row.get("longitude") or "").strip()

            if world_region:
                world_regions.add(world_region)
            if country:
                countries.add(country)

            total_rows += 1
            if len(sample_rows) < max_rows:
                sample_rows.append(
                    f"- {world_region} | {country} | {region} ({latitude}, {longitude})"
                )

    return {
        "total_rows": total_rows,
        "world_regions": tuple(sorted(world_regions)),
        "countries": tuple(sorted(countries)),
        "sample_rows": tuple(sample_rows),
    }


def geography_csv_schema_help_text() -> str:
    columns_line = ",".join(REQUIRED_COLUMNS)
    sample_line = ",".join(SAMPLE_ROW)
    return (
        "Geography CSV Requirements\n"
        "\n"
        "Required header columns (exact order recommended):\n"
        f"{columns_line}\n"
        "\n"
        "Example row:\n"
        f"{sample_line}\n"
        "\n"
        "Notes:\n"
        "- world_region, country, and region must be non-empty text.\n"
        "- latitude and longitude must be numeric decimal values.\n"
        "- planning profile fields must be numeric."
    )


def _load_region_profiles() -> tuple[RegionProfile, ...]:
    csv_path = geography_csv_path()
    if not csv_path.exists():
        return ()

    profiles: list[RegionProfile] = []
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            try:
                latitude = float(row.get("latitude") or 0.0)
                longitude = float(row.get("longitude") or 0.0)
                infrastructure_damage_percent = float(
                    row.get("infrastructure_damage_percent") or 0.0
                )
                road_access_score = float(row.get("road_access_score") or 0.0)
                health_operability_score = float(
                    row.get("health_operability_score") or 0.0
                )
                local_water_liters_per_day = float(
                    row.get("local_water_liters_per_day") or 0.0
                )
                local_food_supply_ratio = float(
                    row.get("local_food_supply_ratio") or 0.0
                )
            except ValueError:
                continue

            profiles.append(
                RegionProfile(
                    world_region=(row.get("world_region") or "").strip(),
                    country=(row.get("country") or "").strip(),
                    region=(row.get("region") or "").strip(),
                    latitude=latitude,
                    longitude=longitude,
                    infrastructure_damage_percent=infrastructure_damage_percent,
                    road_access_score=road_access_score,
                    health_operability_score=health_operability_score,
                    local_water_liters_per_day=local_water_liters_per_day,
                    local_food_supply_ratio=local_food_supply_ratio,
                )
            )

    # Keep only complete rows and stable ordering.
    cleaned = [
        profile
        for profile in profiles
        if profile.world_region and profile.country and profile.region
    ]
    cleaned.sort(key=lambda p: (p.world_region, p.country, p.region))
    if cleaned:
        return tuple(cleaned)

    return (
        RegionProfile(
            world_region="North America",
            country="United States",
            region="Gulf Coast",
            latitude=29.7604,
            longitude=-95.3698,
            infrastructure_damage_percent=35.0,
            road_access_score=0.72,
            health_operability_score=0.82,
            local_water_liters_per_day=34000.0,
            local_food_supply_ratio=0.32,
        ),
    )


_REGION_PROFILES: tuple[RegionProfile, ...] = _load_region_profiles()


def reload_region_profiles() -> int:
    global _REGION_PROFILES
    _REGION_PROFILES = _load_region_profiles()
    return len(_REGION_PROFILES)


def list_world_regions() -> tuple[str, ...]:
    return tuple(sorted({profile.world_region for profile in _REGION_PROFILES}))


def list_countries() -> tuple[str, ...]:
    return tuple(sorted({profile.country for profile in _REGION_PROFILES}))


def list_countries_for_world_region(world_region: str) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                profile.country
                for profile in _REGION_PROFILES
                if profile.world_region == world_region
            }
        )
    )


def list_regions(country: str) -> tuple[str, ...]:
    return tuple(
        profile.region for profile in _REGION_PROFILES if profile.country == country
    )


def get_region_profile(country: str, region: str) -> RegionProfile | None:
    for profile in _REGION_PROFILES:
        if profile.country == country and profile.region == region:
            return profile
    return None


def get_world_region_for_country(country: str) -> str | None:
    for profile in _REGION_PROFILES:
        if profile.country == country:
            return profile.world_region
    return None


def parse_location_label(location_label: str) -> tuple[str | None, str | None]:
    if " | " not in location_label:
        return None, None
    parts = location_label.split(" | ", 1)
    country = parts[0].strip()
    region = parts[1].strip()
    if not country or not region:
        return None, None
    return country, region


def format_location_label(country: str | None, region: str | None, fallback: str = "Unassigned Region") -> str:
    if country and region:
        return f"{country} | {region}"
    return fallback
