from __future__ import annotations

from dataclasses import dataclass


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


_WORLD_REGION_DEFAULTS: dict[str, tuple[float, float, float, float, float]] = {
    "North America": (31.0, 0.76, 0.82, 34000.0, 0.32),
    "Latin America": (35.0, 0.66, 0.71, 23000.0, 0.24),
    "Europe": (24.0, 0.83, 0.88, 30000.0, 0.39),
    "Middle East": (39.0, 0.59, 0.63, 17000.0, 0.18),
    "North Africa": (37.0, 0.60, 0.64, 18000.0, 0.19),
    "West Africa": (38.0, 0.55, 0.59, 16000.0, 0.17),
    "East Africa": (36.0, 0.58, 0.62, 17500.0, 0.19),
    "Southern Africa": (34.0, 0.62, 0.67, 21000.0, 0.22),
    "South Asia": (41.0, 0.56, 0.60, 16500.0, 0.16),
    "Southeast Asia": (39.0, 0.60, 0.64, 21000.0, 0.20),
    "East Asia": (29.0, 0.78, 0.84, 29000.0, 0.34),
    "Central Asia": (35.0, 0.58, 0.63, 18000.0, 0.20),
    "Oceania": (27.0, 0.80, 0.86, 31000.0, 0.36),
}


def _profile(
    world_region: str,
    country: str,
    region: str,
    latitude: float,
    longitude: float,
    damage_delta: float = 0.0,
    road_delta: float = 0.0,
    health_delta: float = 0.0,
    water_delta: float = 0.0,
    food_delta: float = 0.0,
) -> RegionProfile:
    damage, road, health, water, food = _WORLD_REGION_DEFAULTS[world_region]
    return RegionProfile(
        world_region=world_region,
        country=country,
        region=region,
        latitude=latitude,
        longitude=longitude,
        infrastructure_damage_percent=max(10.0, min(70.0, damage + damage_delta)),
        road_access_score=max(0.2, min(0.95, road + road_delta)),
        health_operability_score=max(0.2, min(0.95, health + health_delta)),
        local_water_liters_per_day=max(6000.0, water + water_delta),
        local_food_supply_ratio=max(0.05, min(0.75, food + food_delta)),
    )


_REGION_PROFILES: tuple[RegionProfile, ...] = (
    # North America
    _profile("North America", "United States", "Gulf Coast", 29.7604, -95.3698, damage_delta=4.0, road_delta=-0.04),
    _profile("North America", "United States", "California", 34.0522, -118.2437, damage_delta=2.0, road_delta=0.01),
    _profile("North America", "Canada", "British Columbia", 49.2827, -123.1207, damage_delta=-3.0, health_delta=0.04),
    _profile("North America", "Canada", "Quebec", 45.5017, -73.5673, damage_delta=-4.0, road_delta=0.02),
    _profile("North America", "Mexico", "Yucatan", 20.9674, -89.5926, damage_delta=5.0, road_delta=-0.06, water_delta=-4000.0),
    _profile("North America", "Mexico", "Oaxaca", 17.0732, -96.7266, damage_delta=6.0, road_delta=-0.08, health_delta=-0.05),

    # Latin America
    _profile("Latin America", "Brazil", "Sao Paulo", -23.5505, -46.6333, damage_delta=-2.0, road_delta=0.05),
    _profile("Latin America", "Brazil", "Pernambuco", -8.0476, -34.8770, damage_delta=4.0, road_delta=-0.04),
    _profile("Latin America", "Argentina", "Buenos Aires Province", -34.6037, -58.3816, damage_delta=-2.0, health_delta=0.02),
    _profile("Latin America", "Chile", "Valparaiso", -33.0472, -71.6127, damage_delta=-1.0, road_delta=0.03),
    _profile("Latin America", "Colombia", "Antioquia", 6.2442, -75.5812, damage_delta=2.0, road_delta=-0.02),
    _profile("Latin America", "Peru", "Lima Region", -12.0464, -77.0428, damage_delta=1.0, water_delta=-2000.0),

    # Europe
    _profile("Europe", "United Kingdom", "England", 51.5072, -0.1276, damage_delta=-4.0, health_delta=0.03),
    _profile("Europe", "France", "Ile-de-France", 48.8566, 2.3522, damage_delta=-4.0, road_delta=0.03),
    _profile("Europe", "Germany", "Bavaria", 48.1351, 11.5820, damage_delta=-5.0, health_delta=0.04),
    _profile("Europe", "Italy", "Sicily", 38.1157, 13.3615, damage_delta=1.0, road_delta=-0.02),
    _profile("Europe", "Spain", "Andalusia", 37.3891, -5.9845, damage_delta=0.0, water_delta=-3000.0),
    _profile("Europe", "Ukraine", "Kyiv Oblast", 50.4501, 30.5234, damage_delta=7.0, road_delta=-0.10, health_delta=-0.08),

    # Middle East
    _profile("Middle East", "Turkey", "Southeastern Anatolia", 37.0662, 37.3833, damage_delta=4.0, road_delta=-0.02),
    _profile("Middle East", "Saudi Arabia", "Riyadh Province", 24.7136, 46.6753, damage_delta=-1.0, water_delta=-5000.0),
    _profile("Middle East", "Jordan", "Amman Governorate", 31.9454, 35.9284, damage_delta=0.0, water_delta=-4500.0),
    _profile("Middle East", "Iraq", "Baghdad Governorate", 33.3152, 44.3661, damage_delta=8.0, road_delta=-0.12, health_delta=-0.1),
    _profile("Middle East", "Lebanon", "Mount Lebanon", 33.8938, 35.5018, damage_delta=3.0, road_delta=-0.04),
    _profile("Middle East", "Yemen", "Aden Governorate", 12.7855, 45.0187, damage_delta=12.0, road_delta=-0.18, health_delta=-0.16),

    # North Africa
    _profile("North Africa", "Egypt", "Cairo Governorate", 30.0444, 31.2357, damage_delta=1.0, road_delta=0.01),
    _profile("North Africa", "Morocco", "Casablanca-Settat", 33.5731, -7.5898, damage_delta=-1.0, road_delta=0.02),
    _profile("North Africa", "Algeria", "Algiers Province", 36.7538, 3.0588, damage_delta=0.0),
    _profile("North Africa", "Tunisia", "Tunis Governorate", 36.8065, 10.1815, damage_delta=-1.0, road_delta=0.02),
    _profile("North Africa", "Libya", "Tripoli District", 32.8872, 13.1913, damage_delta=7.0, road_delta=-0.11, health_delta=-0.1),

    # West Africa
    _profile("West Africa", "Nigeria", "Lagos State", 6.5244, 3.3792, damage_delta=2.0, road_delta=0.01),
    _profile("West Africa", "Ghana", "Greater Accra", 5.6037, -0.1870, damage_delta=0.0, road_delta=0.02),
    _profile("West Africa", "Senegal", "Dakar Region", 14.7167, -17.4677, damage_delta=-1.0),
    _profile("West Africa", "Cote d'Ivoire", "Abidjan Autonomous District", 5.3600, -4.0083, damage_delta=1.0),
    _profile("West Africa", "Mali", "Bamako District", 12.6392, -8.0029, damage_delta=7.0, road_delta=-0.12, health_delta=-0.1),
    _profile("West Africa", "Niger", "Niamey Region", 13.5116, 2.1254, damage_delta=8.0, road_delta=-0.13, water_delta=-3000.0),

    # East Africa
    _profile("East Africa", "Kenya", "Nairobi County", -1.2864, 36.8172, damage_delta=-2.0, road_delta=0.06),
    _profile("East Africa", "Ethiopia", "Addis Ababa", 8.9806, 38.7578, damage_delta=1.0),
    _profile("East Africa", "Tanzania", "Dar es Salaam", -6.7924, 39.2083, damage_delta=2.0, road_delta=-0.01),
    _profile("East Africa", "Uganda", "Central Region", 0.3476, 32.5825, damage_delta=1.0),
    _profile("East Africa", "Rwanda", "Kigali City", -1.9441, 30.0619, damage_delta=-1.0, road_delta=0.03),
    _profile("East Africa", "Somalia", "Banadir", 2.0469, 45.3182, damage_delta=11.0, road_delta=-0.2, health_delta=-0.18),

    # Southern Africa
    _profile("Southern Africa", "South Africa", "Gauteng", -26.2041, 28.0473, damage_delta=-1.0, road_delta=0.05),
    _profile("Southern Africa", "South Africa", "Western Cape", -33.9249, 18.4241, damage_delta=-2.0, road_delta=0.04),
    _profile("Southern Africa", "Botswana", "South-East District", -24.6282, 25.9231, damage_delta=-3.0),
    _profile("Southern Africa", "Zimbabwe", "Harare Province", -17.8292, 31.0522, damage_delta=2.0, road_delta=-0.04),
    _profile("Southern Africa", "Mozambique", "Sofala", -19.8349, 34.8389, damage_delta=7.0, road_delta=-0.1),

    # South Asia
    _profile("South Asia", "India", "Maharashtra", 19.0760, 72.8777, damage_delta=-1.0, road_delta=0.04),
    _profile("South Asia", "India", "West Bengal", 22.5726, 88.3639, damage_delta=3.0, road_delta=-0.03),
    _profile("South Asia", "Pakistan", "Sindh", 24.8607, 67.0011, damage_delta=4.0, road_delta=-0.05),
    _profile("South Asia", "Bangladesh", "Dhaka Division", 23.8103, 90.4125, damage_delta=6.0, road_delta=-0.07),
    _profile("South Asia", "Sri Lanka", "Western Province", 6.9271, 79.8612, damage_delta=0.0, road_delta=0.01),
    _profile("South Asia", "Nepal", "Bagmati Province", 27.7172, 85.3240, damage_delta=5.0, road_delta=-0.1, health_delta=-0.06),

    # Southeast Asia
    _profile("Southeast Asia", "Philippines", "Central Luzon", 15.4828, 120.7134, damage_delta=1.0),
    _profile("Southeast Asia", "Indonesia", "Jakarta", -6.2088, 106.8456, damage_delta=2.0),
    _profile("Southeast Asia", "Indonesia", "Aceh", 5.5483, 95.3238, damage_delta=5.0, road_delta=-0.06),
    _profile("Southeast Asia", "Thailand", "Bangkok Metropolitan", 13.7563, 100.5018, damage_delta=-2.0, road_delta=0.05),
    _profile("Southeast Asia", "Vietnam", "Ho Chi Minh City", 10.8231, 106.6297, damage_delta=0.0),
    _profile("Southeast Asia", "Myanmar", "Yangon Region", 16.8409, 96.1735, damage_delta=5.0, road_delta=-0.07, health_delta=-0.06),

    # East Asia
    _profile("East Asia", "Japan", "Kansai", 34.6937, 135.5023, damage_delta=-3.0, road_delta=0.03),
    _profile("East Asia", "Japan", "Tohoku", 38.2682, 140.8694, damage_delta=2.0, road_delta=-0.02),
    _profile("East Asia", "China", "Guangdong", 23.1291, 113.2644, damage_delta=-1.0, road_delta=0.03),
    _profile("East Asia", "China", "Sichuan", 30.5728, 104.0668, damage_delta=2.0, road_delta=-0.04),
    _profile("East Asia", "South Korea", "Seoul Capital Area", 37.5665, 126.9780, damage_delta=-4.0, road_delta=0.04),
    _profile("East Asia", "Mongolia", "Ulaanbaatar", 47.8864, 106.9057, damage_delta=1.0, water_delta=-3000.0),

    # Central Asia
    _profile("Central Asia", "Kazakhstan", "Almaty Region", 43.2389, 76.8897, damage_delta=-1.0, road_delta=0.02),
    _profile("Central Asia", "Uzbekistan", "Tashkent Region", 41.2995, 69.2401, damage_delta=0.0),
    _profile("Central Asia", "Kyrgyzstan", "Chuy Region", 42.8746, 74.5698, damage_delta=2.0, road_delta=-0.06),
    _profile("Central Asia", "Tajikistan", "Dushanbe", 38.5598, 68.7870, damage_delta=3.0, road_delta=-0.08),

    # Oceania
    _profile("Oceania", "Australia", "New South Wales", -33.8688, 151.2093, damage_delta=-3.0, road_delta=0.03),
    _profile("Oceania", "Australia", "Queensland", -27.4698, 153.0251, damage_delta=1.0, road_delta=0.0),
    _profile("Oceania", "New Zealand", "Auckland Region", -36.8485, 174.7633, damage_delta=-4.0, health_delta=0.03),
    _profile("Oceania", "Papua New Guinea", "National Capital District", -9.4438, 147.1803, damage_delta=8.0, road_delta=-0.13),
    _profile("Oceania", "Fiji", "Central Division", -18.1248, 178.4501, damage_delta=4.0, road_delta=-0.06),
)


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
