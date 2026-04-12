from __future__ import annotations

from dataclasses import replace
from uuid import uuid4

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


def build_default_operational_assets() -> tuple[tuple[InventoryPosition, ...], tuple[PersonnelRole, ...], tuple[TransportAsset, ...]]:
    resources = (
        InventoryPosition("Water reserve", "water", 800000.0, "liters", 1),
        InventoryPosition("Emergency ration stock", "food", 24000000.0, "kcal", 1),
        InventoryPosition("Shelter kits", "shelter", 8000.0, "kg", 2),
    )
    personnel = (
        PersonnelRole("Medical", 45, 8.0, 42.0, volunteers=8),
        PersonnelRole("Logistics", 60, 8.0, 28.0, volunteers=20),
        PersonnelRole("Engineering", 20, 8.0, 39.0, volunteers=4),
        PersonnelRole("Coordination", 15, 8.0, 34.0, volunteers=2),
    )
    transportation = (
        TransportAsset("Cargo truck", 12000.0, 18, 55.0, 0.82, 2.8),
        TransportAsset("Medium helicopter", 3500.0, 2, 180.0, 0.7, 18.0),
    )
    return resources, personnel, transportation


def build_default_scenario(name: str = "New Planning Scenario") -> Scenario:
    timestamp = utc_now()
    resources, personnel, transportation = build_default_operational_assets()
    return Scenario(
        scenario_id=uuid4().hex,
        project_id=uuid4().hex,
        name=name,
        status=ScenarioStatus.DRAFT,
        hazard_profile=HazardProfile(
            hazard_type=HazardType.FLOOD,
            severity_band="moderate",
            duration_days=5,
            location_label="Unassigned Region",
            infrastructure_damage_percent=25.0,
        ),
        population_profile=PopulationProfile(
            total_population=5000,
            displaced_population=1800,
            children_under_five=420,
            older_adults=380,
            pregnant_or_lactating_people=110,
            medically_vulnerable_population=210,
        ),
        infrastructure_profile=InfrastructureProfile(
            road_access_score=0.75,
            health_facility_operability_score=0.8,
            local_water_availability_liters_per_day=25000.0,
            local_food_supply_ratio=0.2,
        ),
        resources=resources,
        personnel=personnel,
        transportation=transportation,
        created_at=timestamp,
        updated_at=timestamp,
        notes="Editable baseline scenario generated from default operational assets.",
    )


def build_seed_scenario() -> Scenario:
    seed = build_default_scenario("Earthquake Baseline Planning Scenario")
    return replace(
        seed,
        scenario_id="seed-earthquake-scenario",
        project_id="seed-project",
        name="Earthquake Baseline Planning Scenario",
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
        notes="Seed scenario used to validate the first desktop planning slice.",
    )