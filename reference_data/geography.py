from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RegionProfile:
    country: str
    region: str
    latitude: float
    longitude: float
    infrastructure_damage_percent: float
    road_access_score: float
    health_operability_score: float
    local_water_liters_per_day: float
    local_food_supply_ratio: float


_REGION_PROFILES: tuple[RegionProfile, ...] = (
    RegionProfile(
        country="United States",
        region="Gulf Coast",
        latitude=29.7604,
        longitude=-95.3698,
        infrastructure_damage_percent=35.0,
        road_access_score=0.72,
        health_operability_score=0.78,
        local_water_liters_per_day=32000.0,
        local_food_supply_ratio=0.28,
    ),
    RegionProfile(
        country="Japan",
        region="Kansai",
        latitude=34.6937,
        longitude=135.5023,
        infrastructure_damage_percent=26.0,
        road_access_score=0.81,
        health_operability_score=0.86,
        local_water_liters_per_day=28000.0,
        local_food_supply_ratio=0.35,
    ),
    RegionProfile(
        country="Kenya",
        region="Nairobi County",
        latitude=-1.2864,
        longitude=36.8172,
        infrastructure_damage_percent=31.0,
        road_access_score=0.64,
        health_operability_score=0.67,
        local_water_liters_per_day=18000.0,
        local_food_supply_ratio=0.22,
    ),
    RegionProfile(
        country="Philippines",
        region="Central Luzon",
        latitude=15.4828,
        longitude=120.7134,
        infrastructure_damage_percent=40.0,
        road_access_score=0.59,
        health_operability_score=0.63,
        local_water_liters_per_day=21000.0,
        local_food_supply_ratio=0.19,
    ),
    RegionProfile(
        country="Turkey",
        region="Southeastern Anatolia",
        latitude=37.0662,
        longitude=37.3833,
        infrastructure_damage_percent=43.0,
        road_access_score=0.57,
        health_operability_score=0.61,
        local_water_liters_per_day=16500.0,
        local_food_supply_ratio=0.17,
    ),
)


def list_countries() -> tuple[str, ...]:
    return tuple(sorted({profile.country for profile in _REGION_PROFILES}))


def list_regions(country: str) -> tuple[str, ...]:
    return tuple(
        profile.region for profile in _REGION_PROFILES if profile.country == country
    )


def get_region_profile(country: str, region: str) -> RegionProfile | None:
    for profile in _REGION_PROFILES:
        if profile.country == country and profile.region == region:
            return profile
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
