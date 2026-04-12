from __future__ import annotations

from engine.contracts import CostResult, NeedsResult
from domain.models import Scenario


def compute_costs(scenario: Scenario, needs: NeedsResult, transport_reliability_buffer: float) -> CostResult:
    days = scenario.hazard_profile.duration_days

    personnel_cost = sum(
        role.count * role.shift_hours * role.hourly_cost * days for role in scenario.personnel
    )
    transport_cost = sum(
        asset.quantity * asset.cost_per_km * 100 * days * transport_reliability_buffer
        for asset in scenario.transportation
    )
    procurement_cost = (
        max(needs.water_required_liters - needs.water_available_liters, 0.0) * 0.002
        + max(needs.food_required_kcal - needs.food_available_kcal, 0.0) * 0.0005
    )

    return CostResult(
        personnel_cost=personnel_cost,
        transport_cost=transport_cost,
        procurement_cost=procurement_cost,
        total_cost=personnel_cost + transport_cost + procurement_cost,
    )
