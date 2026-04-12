from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from domain.enums import AssumptionCategory, ConfidenceLevel, HazardType, ScenarioStatus


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class AssumptionRecord:
    identifier: str
    title: str
    category: AssumptionCategory
    unit: str
    baseline_value: float
    source_name: str
    source_version: str
    rationale: str
    hazard_types: tuple[HazardType, ...]
    override_allowed: bool = True
    confidence_level: ConfidenceLevel = ConfidenceLevel.BASELINE
    recommended_min: float | None = None
    recommended_max: float | None = None


@dataclass(frozen=True)
class HazardProfile:
    hazard_type: HazardType
    severity_band: str
    duration_days: int
    location_label: str
    infrastructure_damage_percent: float


@dataclass(frozen=True)
class PopulationProfile:
    total_population: int
    displaced_population: int
    children_under_five: int = 0
    older_adults: int = 0
    pregnant_or_lactating_people: int = 0
    medically_vulnerable_population: int = 0


@dataclass(frozen=True)
class InfrastructureProfile:
    road_access_score: float
    health_facility_operability_score: float
    local_water_availability_liters_per_day: float
    local_food_supply_ratio: float


@dataclass(frozen=True)
class InventoryPosition:
    name: str
    category: str
    quantity: float
    unit: str
    priority_rank: int


@dataclass(frozen=True)
class PersonnelRole:
    name: str
    count: int
    shift_hours: float
    hourly_cost: float
    volunteers: int = 0


@dataclass(frozen=True)
class TransportAsset:
    name: str
    capacity_kg: float
    quantity: int
    speed_kmh: float
    reliability_score: float
    cost_per_km: float


@dataclass(frozen=True)
class Scenario:
    scenario_id: str
    project_id: str
    name: str
    status: ScenarioStatus
    hazard_profile: HazardProfile
    population_profile: PopulationProfile
    infrastructure_profile: InfrastructureProfile
    resources: tuple[InventoryPosition, ...] = ()
    personnel: tuple[PersonnelRole, ...] = ()
    transportation: tuple[TransportAsset, ...] = ()
    variant_label: str = "baseline"
    base_scenario_id: str | None = None
    world_region: str | None = None
    country: str | None = None
    region: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    notes: str = ""

    @classmethod
    def create(cls, name: str, hazard_profile: HazardProfile, population_profile: PopulationProfile, infrastructure_profile: InfrastructureProfile) -> "Scenario":
        timestamp = utc_now()
        scenario_id = uuid4().hex
        project_id = uuid4().hex
        return cls(
            scenario_id=scenario_id,
            project_id=project_id,
            name=name,
            status=ScenarioStatus.DRAFT,
            hazard_profile=hazard_profile,
            population_profile=population_profile,
            infrastructure_profile=infrastructure_profile,
            created_at=timestamp,
            updated_at=timestamp,
        )


@dataclass(frozen=True)
class ScenarioSummary:
    scenario_id: str
    name: str
    variant_label: str
    base_scenario_id: str | None
    hazard_type: HazardType
    severity_band: str
    location_label: str
    status: ScenarioStatus
    updated_at: datetime


@dataclass(frozen=True)
class RiskFlag:
    code: str
    title: str
    detail: str
    confidence_level: ConfidenceLevel


@dataclass(frozen=True)
class AnalysisSummary:
    critical_coverage_percent: float
    overall_coverage_percent: float
    total_estimated_cost: float
    confidence_level: ConfidenceLevel
    unmet_critical_needs: tuple[str, ...]
    risk_flags: tuple[RiskFlag, ...] = ()
    assumptions_trace: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)