from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class AssumptionIndex:
    water_liters_per_person_per_day: float
    food_kcal_per_person_per_day: float
    staffing_shift_hours_per_day: float
    transport_reliability_buffer: float
    contingency_ratio: float


@dataclass(frozen=True)
class NeedsResult:
    water_required_liters: float
    water_available_liters: float
    water_coverage: float
    food_required_kcal: float
    food_available_kcal: float
    food_coverage: float


@dataclass(frozen=True)
class StaffingResult:
    total_required_hours: float
    total_available_hours: float
    coverage: float
    required_by_role: dict[str, float] = field(default_factory=dict)
    available_by_role: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class TransportResult:
    required_mass_kg: float
    available_capacity_kg: float
    coverage: float
    estimated_waves: int


@dataclass(frozen=True)
class CostResult:
    personnel_cost: float
    transport_cost: float
    procurement_cost: float
    total_cost: float
