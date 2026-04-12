from __future__ import annotations

from engine.contracts import AssumptionIndex, StaffingResult
from domain.models import Scenario


def compute_staffing(scenario: Scenario, assumptions: AssumptionIndex) -> StaffingResult:
    days = scenario.hazard_profile.duration_days
    population = scenario.population_profile.total_population
    displaced_population = max(scenario.population_profile.displaced_population, 0)

    required_by_role = {
        "medical": population / 1000 * 48 * days,
        "logistics": max(displaced_population, population * 0.35) / 1000 * 36 * days,
        "engineering": population / 1000 * 16 * days,
        "coordination": population / 1000 * 12 * days,
    }

    total_required_hours = sum(required_by_role.values())

    available_by_role: dict[str, float] = {}
    total_available_hours = 0.0
    for role in scenario.personnel:
        usable_shift_hours = min(role.shift_hours, assumptions.staffing_shift_hours_per_day)
        role_hours = role.count * usable_shift_hours * days
        volunteer_hours = role.volunteers * (usable_shift_hours * 0.75) * days
        available = role_hours + volunteer_hours
        available_by_role[role.name.lower()] = available
        total_available_hours += available

    coverage = min(1.0, total_available_hours / total_required_hours) if total_required_hours else 1.0

    return StaffingResult(
        total_required_hours=total_required_hours,
        total_available_hours=total_available_hours,
        coverage=coverage,
        required_by_role=required_by_role,
        available_by_role=available_by_role,
    )
