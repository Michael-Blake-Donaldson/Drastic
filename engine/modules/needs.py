from __future__ import annotations

from engine.contracts import AssumptionIndex, NeedsResult
from domain.models import Scenario


def compute_needs(scenario: Scenario, assumptions: AssumptionIndex) -> NeedsResult:
    days = scenario.hazard_profile.duration_days
    population = scenario.population_profile.total_population
    contingency_multiplier = 1.0 + assumptions.contingency_ratio

    water_required = (
        population
        * days
        * assumptions.water_liters_per_person_per_day
        * contingency_multiplier
    )
    local_water_offset = scenario.infrastructure_profile.local_water_availability_liters_per_day * days
    water_available = local_water_offset + _resource_quantity(scenario, "water", "liters")

    food_required = (
        population
        * days
        * assumptions.food_kcal_per_person_per_day
        * contingency_multiplier
    )
    local_food_ratio = max(0.0, min(scenario.infrastructure_profile.local_food_supply_ratio, 1.0))
    local_food_offset = food_required * local_food_ratio
    food_available = local_food_offset + _resource_quantity(scenario, "food", "kcal")

    water_coverage = min(1.0, water_available / water_required) if water_required else 1.0
    food_coverage = min(1.0, food_available / food_required) if food_required else 1.0

    return NeedsResult(
        water_required_liters=water_required,
        water_available_liters=water_available,
        water_coverage=water_coverage,
        food_required_kcal=food_required,
        food_available_kcal=food_available,
        food_coverage=food_coverage,
    )


def _resource_quantity(scenario: Scenario, category: str, unit: str) -> float:
    total = 0.0
    for resource in scenario.resources:
        if resource.category == category and resource.unit == unit:
            total += resource.quantity
    return total
