from __future__ import annotations

from time import perf_counter

from domain.enums import ConfidenceLevel
from domain.models import AnalysisSummary, AssumptionRecord, RiskFlag, Scenario
from engine.contracts import AssumptionIndex
from engine.modules.costs import compute_costs
from engine.modules.needs import compute_needs
from engine.modules.staffing import compute_staffing
from engine.modules.transport import compute_transport


class PlanningEngine:
    def __init__(self, assumption_registry: tuple[AssumptionRecord, ...]) -> None:
        self.assumption_registry = assumption_registry
        self.assumption_index = self._build_index(assumption_registry)

    def analyze(self, scenario: Scenario) -> AnalysisSummary:
        started = perf_counter()

        step_started = perf_counter()
        needs = compute_needs(scenario, self.assumption_index)
        needs_ms = (perf_counter() - step_started) * 1000.0

        step_started = perf_counter()
        staffing = compute_staffing(scenario, self.assumption_index)
        staffing_ms = (perf_counter() - step_started) * 1000.0

        step_started = perf_counter()
        transport = compute_transport(scenario, self.assumption_index)
        transport_ms = (perf_counter() - step_started) * 1000.0

        step_started = perf_counter()
        costs = compute_costs(
            scenario,
            needs,
            transport_reliability_buffer=self.assumption_index.transport_reliability_buffer,
        )
        costs_ms = (perf_counter() - step_started) * 1000.0

        water_coverage = needs.water_coverage
        food_coverage = needs.food_coverage
        staffing_coverage = staffing.coverage
        transport_coverage = transport.coverage

        critical_coverage = min(water_coverage, food_coverage, staffing_coverage, transport_coverage)
        overall_coverage = (water_coverage + food_coverage + staffing_coverage + transport_coverage) / 4

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

        if transport.estimated_delivery_days > scenario.hazard_profile.duration_days:
            risk_flags.append(
                RiskFlag(
                    code="delivery_window_exceeded",
                    title="Delivery window exceeded",
                    detail="Estimated delivery time exceeds the scenario duration assumptions, indicating likely timeline slippage.",
                    confidence_level=ConfidenceLevel.CONDITIONAL,
                )
            )

        confidence = ConfidenceLevel.CONDITIONAL
        if (
            scenario.population_profile.total_population <= 0
            or not scenario.resources
            or not scenario.personnel
            or not scenario.transportation
        ):
            confidence = ConfidenceLevel.LOW
            risk_flags.append(
                RiskFlag(
                    code="low_confidence_incomplete_inputs",
                    title="Incomplete scenario inputs",
                    detail="One or more required operational sections are empty or invalid, lowering confidence in planning outputs.",
                    confidence_level=ConfidenceLevel.LOW,
                )
            )

        metadata = {
            "water_required_liters": round(needs.water_required_liters, 2),
            "water_available_liters": round(needs.water_available_liters, 2),
            "food_required_kcal": round(needs.food_required_kcal, 2),
            "food_available_kcal": round(needs.food_available_kcal, 2),
            "staff_hours_required": round(staffing.total_required_hours, 2),
            "staff_hours_available": round(staffing.total_available_hours, 2),
            "transport_mass_required_kg": round(transport.required_mass_kg, 2),
            "transport_capacity_kg": round(transport.available_capacity_kg, 2),
            "transport_estimated_waves": transport.estimated_waves,
            "transport_estimated_delivery_days": round(transport.estimated_delivery_days, 2),
            "transport_daily_movable_capacity_kg": round(transport.daily_movable_capacity_kg, 2),
            "transport_assumed_route_distance_km": round(transport.assumed_route_distance_km, 2),
            "transport_average_speed_kmh": round(transport.average_speed_kmh, 2),
            "personnel_cost": round(costs.personnel_cost, 2),
            "transport_cost": round(costs.transport_cost, 2),
            "procurement_cost": round(costs.procurement_cost, 2),
            "staffing_required_by_role": {
                role: round(value, 2) for role, value in staffing.required_by_role.items()
            },
            "staffing_available_by_role": {
                role: round(value, 2) for role, value in staffing.available_by_role.items()
            },
            "perf_needs_ms": round(needs_ms, 3),
            "perf_staffing_ms": round(staffing_ms, 3),
            "perf_transport_ms": round(transport_ms, 3),
            "perf_costs_ms": round(costs_ms, 3),
            "perf_total_analyze_ms": round((perf_counter() - started) * 1000.0, 3),
        }

        return AnalysisSummary(
            critical_coverage_percent=round(critical_coverage * 100, 1),
            overall_coverage_percent=round(overall_coverage * 100, 1),
            total_estimated_cost=round(costs.total_cost, 2),
            confidence_level=confidence,
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
