from __future__ import annotations

from datetime import datetime

from domain.enums import HazardType, ScenarioStatus
from domain.models import (
    HazardProfile,
    InfrastructureProfile,
    InventoryPosition,
    PersonnelRole,
    PopulationProfile,
    Scenario,
    TransportAsset,
)


def scenario_to_dict(scenario: Scenario) -> dict[str, object]:
    return {
        "scenario_id": scenario.scenario_id,
        "project_id": scenario.project_id,
        "name": scenario.name,
        "variant_label": scenario.variant_label,
        "base_scenario_id": scenario.base_scenario_id,
        "country": scenario.country,
        "region": scenario.region,
        "latitude": scenario.latitude,
        "longitude": scenario.longitude,
        "status": scenario.status.value,
        "hazard_profile": {
            "hazard_type": scenario.hazard_profile.hazard_type.value,
            "severity_band": scenario.hazard_profile.severity_band,
            "duration_days": scenario.hazard_profile.duration_days,
            "location_label": scenario.hazard_profile.location_label,
            "infrastructure_damage_percent": scenario.hazard_profile.infrastructure_damage_percent,
        },
        "population_profile": {
            "total_population": scenario.population_profile.total_population,
            "displaced_population": scenario.population_profile.displaced_population,
            "children_under_five": scenario.population_profile.children_under_five,
            "older_adults": scenario.population_profile.older_adults,
            "pregnant_or_lactating_people": scenario.population_profile.pregnant_or_lactating_people,
            "medically_vulnerable_population": scenario.population_profile.medically_vulnerable_population,
        },
        "infrastructure_profile": {
            "road_access_score": scenario.infrastructure_profile.road_access_score,
            "health_facility_operability_score": scenario.infrastructure_profile.health_facility_operability_score,
            "local_water_availability_liters_per_day": scenario.infrastructure_profile.local_water_availability_liters_per_day,
            "local_food_supply_ratio": scenario.infrastructure_profile.local_food_supply_ratio,
        },
        "resources": [
            {
                "name": resource.name,
                "category": resource.category,
                "quantity": resource.quantity,
                "unit": resource.unit,
                "priority_rank": resource.priority_rank,
            }
            for resource in scenario.resources
        ],
        "personnel": [
            {
                "name": role.name,
                "count": role.count,
                "shift_hours": role.shift_hours,
                "hourly_cost": role.hourly_cost,
                "volunteers": role.volunteers,
            }
            for role in scenario.personnel
        ],
        "transportation": [
            {
                "name": asset.name,
                "capacity_kg": asset.capacity_kg,
                "quantity": asset.quantity,
                "speed_kmh": asset.speed_kmh,
                "reliability_score": asset.reliability_score,
                "cost_per_km": asset.cost_per_km,
            }
            for asset in scenario.transportation
        ],
        "created_at": scenario.created_at.isoformat(),
        "updated_at": scenario.updated_at.isoformat(),
        "notes": scenario.notes,
    }


def scenario_from_dict(payload: dict[str, object]) -> Scenario:
    hazard_payload = payload["hazard_profile"]
    population_payload = payload["population_profile"]
    infrastructure_payload = payload["infrastructure_profile"]
    assert isinstance(hazard_payload, dict)
    assert isinstance(population_payload, dict)
    assert isinstance(infrastructure_payload, dict)

    return Scenario(
        scenario_id=str(payload["scenario_id"]),
        project_id=str(payload["project_id"]),
        name=str(payload["name"]),
        variant_label=str(payload.get("variant_label", "baseline")),
        base_scenario_id=(
            str(payload["base_scenario_id"]) if payload.get("base_scenario_id") is not None else None
        ),
        country=str(payload["country"]) if payload.get("country") is not None else None,
        region=str(payload["region"]) if payload.get("region") is not None else None,
        latitude=float(payload["latitude"]) if payload.get("latitude") is not None else None,
        longitude=float(payload["longitude"]) if payload.get("longitude") is not None else None,
        status=ScenarioStatus(str(payload["status"])),
        hazard_profile=HazardProfile(
            hazard_type=HazardType(str(hazard_payload["hazard_type"])),
            severity_band=str(hazard_payload["severity_band"]),
            duration_days=int(hazard_payload["duration_days"]),
            location_label=str(hazard_payload["location_label"]),
            infrastructure_damage_percent=float(hazard_payload["infrastructure_damage_percent"]),
        ),
        population_profile=PopulationProfile(
            total_population=int(population_payload["total_population"]),
            displaced_population=int(population_payload["displaced_population"]),
            children_under_five=int(population_payload["children_under_five"]),
            older_adults=int(population_payload["older_adults"]),
            pregnant_or_lactating_people=int(population_payload["pregnant_or_lactating_people"]),
            medically_vulnerable_population=int(population_payload["medically_vulnerable_population"]),
        ),
        infrastructure_profile=InfrastructureProfile(
            road_access_score=float(infrastructure_payload["road_access_score"]),
            health_facility_operability_score=float(infrastructure_payload["health_facility_operability_score"]),
            local_water_availability_liters_per_day=float(infrastructure_payload["local_water_availability_liters_per_day"]),
            local_food_supply_ratio=float(infrastructure_payload["local_food_supply_ratio"]),
        ),
        resources=tuple(
            InventoryPosition(
                name=str(resource["name"]),
                category=str(resource["category"]),
                quantity=float(resource["quantity"]),
                unit=str(resource["unit"]),
                priority_rank=int(resource["priority_rank"]),
            )
            for resource in payload.get("resources", [])
            if isinstance(resource, dict)
        ),
        personnel=tuple(
            PersonnelRole(
                name=str(role["name"]),
                count=int(role["count"]),
                shift_hours=float(role["shift_hours"]),
                hourly_cost=float(role["hourly_cost"]),
                volunteers=int(role["volunteers"]),
            )
            for role in payload.get("personnel", [])
            if isinstance(role, dict)
        ),
        transportation=tuple(
            TransportAsset(
                name=str(asset["name"]),
                capacity_kg=float(asset["capacity_kg"]),
                quantity=int(asset["quantity"]),
                speed_kmh=float(asset["speed_kmh"]),
                reliability_score=float(asset["reliability_score"]),
                cost_per_km=float(asset["cost_per_km"]),
            )
            for asset in payload.get("transportation", [])
            if isinstance(asset, dict)
        ),
        created_at=datetime.fromisoformat(str(payload["created_at"])),
        updated_at=datetime.fromisoformat(str(payload["updated_at"])),
        notes=str(payload.get("notes", "")),
    )