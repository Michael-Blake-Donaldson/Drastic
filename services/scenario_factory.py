from __future__ import annotations

from domain.enums import HazardType, ScenarioStatus
from domain.models import (
    HazardProfile,
    InfrastructureProfile,
    InventoryPosition,
    PersonnelRole,
    PopulationProfile,
    Scenario,
    TransportAsset,
    utc_now,
)


def build_seed_scenario() -> Scenario:
    timestamp = utc_now()
    return Scenario(
        scenario_id="seed-earthquake-scenario",
        project_id="seed-project",
        name="Earthquake Baseline Planning Scenario",
        status=ScenarioStatus.DRAFT,
        hazard_profile=HazardProfile(
            hazard_type=HazardType.EARTHQUAKE,
            severity_band="high",
            duration_days=7,
            location_label="Sample Region",
            infrastructure_damage_percent=45.0,
        ),
        population_profile=PopulationProfile(
            total_population=25000,
            displaced_population=12000,
            children_under_five=2200,
            older_adults=1800,
            pregnant_or_lactating_people=650,
            medically_vulnerable_population=1100,
        ),
        infrastructure_profile=InfrastructureProfile(
            road_access_score=0.58,
            health_facility_operability_score=0.62,
            local_water_availability_liters_per_day=90000.0,
            local_food_supply_ratio=0.12,
        ),
        resources=(
            InventoryPosition("Water reserve", "water", 800000.0, "liters", 1),
            InventoryPosition("Emergency ration stock", "food", 24000000.0, "kcal", 1),
            InventoryPosition("Shelter kits", "shelter", 8000.0, "kg", 2),
        ),
        personnel=(
            PersonnelRole("Medical", 45, 8.0, 42.0, volunteers=8),
            PersonnelRole("Logistics", 60, 8.0, 28.0, volunteers=20),
            PersonnelRole("Engineering", 20, 8.0, 39.0, volunteers=4),
            PersonnelRole("Coordination", 15, 8.0, 34.0, volunteers=2),
        ),
        transportation=(
            TransportAsset("Cargo truck", 12000.0, 18, 55.0, 0.82, 2.8),
            TransportAsset("Medium helicopter", 3500.0, 2, 180.0, 0.7, 18.0),
        ),
        created_at=timestamp,
        updated_at=timestamp,
        notes="Seed scenario used to validate the first desktop planning slice.",
    )