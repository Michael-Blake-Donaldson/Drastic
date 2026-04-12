from __future__ import annotations

from dataclasses import dataclass

from domain.enums import ConfidenceLevel
from domain.models import AnalysisSummary, AssumptionRecord, RiskFlag, Scenario


@dataclass(frozen=True)
class AssumptionIndex:
    water_liters_per_person_per_day: float
    food_kcal_per_person_per_day: float
    staffing_shift_hours_per_day: float
    transport_reliability_buffer: float
    contingency_ratio: float


class PlanningEngine:
    def __init__(self, assumption_registry: tuple[AssumptionRecord, ...]) -> None:
        self.assumption_registry = assumption_registry
        self.assumption_index = self._build_index(assumption_registry)

    def analyze(self, scenario: Scenario) -> AnalysisSummary:
        days = scenario.hazard_profile.duration_days
        population = scenario.population_profile.total_population
        displaced_population = max(scenario.population_profile.displaced_population, 0)
        contingency_multiplier = 1.0 + self.assumption_index.contingency_ratio

        water_required = (
            population
            * days
            * self.assumption_index.water_liters_per_person_per_day
            * contingency_multiplier
        )
        local_water_offset = scenario.infrastructure_profile.local_water_availability_liters_per_day * days
        water_available = local_water_offset + self._resource_quantity(scenario, "water", "liters")

        food_required = (
            population
            * days
            * self.assumption_index.food_kcal_per_person_per_day
            * contingency_multiplier
        )
        local_food_ratio = max(0.0, min(scenario.infrastructure_profile.local_food_supply_ratio, 1.0))
        local_food_offset = food_required * local_food_ratio
        food_available = local_food_offset + self._resource_quantity(scenario, "food", "kcal")

        medical_hours_required = population / 1000 * 48 * days
        logistics_hours_required = max(displaced_population, population * 0.35) / 1000 * 36 * days
        engineering_hours_required = population / 1000 * 16 * days
        coordination_hours_required = population / 1000 * 12 * days
        total_staff_hours_required = (
            medical_hours_required
            + logistics_hours_required
            + engineering_hours_required
            + coordination_hours_required
        )
        available_staff_hours = self._available_staff_hours(scenario)

        total_mass_to_move_kg = self._resource_mass_kg(scenario)
        transport_capacity_kg = self._transport_capacity_kg(scenario)

        water_coverage = min(1.0, water_available / water_required) if water_required else 1.0
        food_coverage = min(1.0, food_available / food_required) if food_required else 1.0
        staffing_coverage = (
            min(1.0, available_staff_hours / total_staff_hours_required)
            if total_staff_hours_required
            else 1.0
        )
        transport_coverage = min(1.0, transport_capacity_kg / total_mass_to_move_kg) if total_mass_to_move_kg else 1.0

        critical_coverage = min(water_coverage, food_coverage, staffing_coverage, transport_coverage)
        overall_coverage = (water_coverage + food_coverage + staffing_coverage + transport_coverage) / 4

        personnel_cost = sum(
            role.count * role.shift_hours * role.hourly_cost * days for role in scenario.personnel
        )
        transport_cost = sum(
            asset.quantity * asset.cost_per_km * 100 * days * self.assumption_index.transport_reliability_buffer
            for asset in scenario.transportation
        )
        procurement_cost = (
            max(water_required - water_available, 0) * 0.002
            + max(food_required - food_available, 0) * 0.0005
        )
        total_estimated_cost = personnel_cost + transport_cost + procurement_cost

        unmet_critical_needs = []
        risk_flags = []
        if water_coverage < 1.0:
            unmet_critical_needs.append("Water requirement is not fully covered.")
            risk_flags.append(
                RiskFlag(
                    code="water_shortfall",
                    title="Water shortfall",
                    detail="Available water falls below the minimum planning baseline for the selected scenario.",
                    confidence_level=ConfidenceLevel.CONDITIONAL,
                )
            )
        if food_coverage < 1.0:
            unmet_critical_needs.append("Food energy requirement is not fully covered.")
            risk_flags.append(
                RiskFlag(
                    code="food_shortfall",
                    title="Food shortfall",
                    detail="Available food supply falls below the minimum planning baseline for the selected scenario.",
                    confidence_level=ConfidenceLevel.CONDITIONAL,
                )
            )
        if staffing_coverage < 1.0:
            unmet_critical_needs.append("Staffing hours are insufficient for baseline operations.")
            risk_flags.append(
                RiskFlag(
                    code="staffing_gap",
                    title="Staffing gap",
                    detail="Declared staffing does not satisfy the baseline role-hour requirements for the selected scenario.",
                    confidence_level=ConfidenceLevel.CONDITIONAL,
                )
            )
        if transport_coverage < 1.0:
            unmet_critical_needs.append("Transport capacity cannot move all declared supply mass within the baseline planning window.")
            risk_flags.append(
                RiskFlag(
                    code="transport_gap",
                    title="Transport bottleneck",
                    detail="Declared transport capacity is lower than the baseline resource mass requirement after reliability buffering.",
                    confidence_level=ConfidenceLevel.CONDITIONAL,
                )
            )

        metadata = {
            "water_required_liters": round(water_required, 2),
            "water_available_liters": round(water_available, 2),
            "food_required_kcal": round(food_required, 2),
            "food_available_kcal": round(food_available, 2),
            "staff_hours_required": round(total_staff_hours_required, 2),
            "staff_hours_available": round(available_staff_hours, 2),
            "transport_mass_required_kg": round(total_mass_to_move_kg, 2),
            "transport_capacity_kg": round(transport_capacity_kg, 2),
        }

        return AnalysisSummary(
            critical_coverage_percent=round(critical_coverage * 100, 1),
            overall_coverage_percent=round(overall_coverage * 100, 1),
            total_estimated_cost=round(total_estimated_cost, 2),
            confidence_level=ConfidenceLevel.CONDITIONAL,
            unmet_critical_needs=tuple(unmet_critical_needs),
            risk_flags=tuple(risk_flags),
            assumptions_trace=tuple(record.identifier for record in self.assumption_registry),
            metadata=metadata,
        )

    def _build_index(self, registry: tuple[AssumptionRecord, ...]) -> AssumptionIndex:
        values = {record.identifier: record.baseline_value for record in registry}
        return AssumptionIndex(
            water_liters_per_person_per_day=values["water.minimum_liters_per_person_per_day"],
            food_kcal_per_person_per_day=values["food.minimum_kcal_per_person_per_day"],
            staffing_shift_hours_per_day=values["staffing.shift_hours_per_day"],
            transport_reliability_buffer=values["transport.reliability_buffer"],
            contingency_ratio=values["contingency.general_buffer_ratio"],
        )

    def _resource_quantity(self, scenario: Scenario, category: str, unit: str) -> float:
        total = 0.0
        for resource in scenario.resources:
            if resource.category == category and resource.unit == unit:
                total += resource.quantity
        return total

    def _resource_mass_kg(self, scenario: Scenario) -> float:
        total = 0.0
        for resource in scenario.resources:
            if resource.unit == "kg":
                total += resource.quantity
            elif resource.unit == "liters":
                total += resource.quantity
        return total

    def _available_staff_hours(self, scenario: Scenario) -> float:
        total = 0.0
        for role in scenario.personnel:
            usable_shift_hours = min(role.shift_hours, self.assumption_index.staffing_shift_hours_per_day)
            total += role.count * usable_shift_hours * scenario.hazard_profile.duration_days
            total += role.volunteers * (usable_shift_hours * 0.75) * scenario.hazard_profile.duration_days
        return total

    def _transport_capacity_kg(self, scenario: Scenario) -> float:
        total = 0.0
        for asset in scenario.transportation:
            total += (
                asset.capacity_kg
                * asset.quantity
                * max(min(asset.reliability_score, 1.0), 0.0)
                * self.assumption_index.transport_reliability_buffer
            )
        return total