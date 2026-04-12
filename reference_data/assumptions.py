from __future__ import annotations

from domain.enums import AssumptionCategory, ConfidenceLevel, HazardType
from domain.models import AssumptionRecord


def build_default_assumption_registry() -> tuple[AssumptionRecord, ...]:
    supported_hazards = (
        HazardType.FLOOD,
        HazardType.HURRICANE,
        HazardType.WILDFIRE,
        HazardType.EARTHQUAKE,
        HazardType.CONFLICT_DISPLACEMENT,
    )

    return (
        AssumptionRecord(
            identifier="water.minimum_liters_per_person_per_day",
            title="Minimum daily water planning baseline",
            category=AssumptionCategory.WATER,
            unit="liters/person/day",
            baseline_value=15.0,
            recommended_min=7.5,
            recommended_max=20.0,
            source_name="Sphere Handbook",
            source_version="Planning baseline",
            rationale="Use a conservative daily water planning baseline until a hazard-specific assumption pack is applied.",
            hazard_types=supported_hazards,
        ),
        AssumptionRecord(
            identifier="food.minimum_kcal_per_person_per_day",
            title="Minimum daily food energy planning baseline",
            category=AssumptionCategory.FOOD,
            unit="kcal/person/day",
            baseline_value=2100.0,
            recommended_min=1800.0,
            recommended_max=2400.0,
            source_name="Humanitarian food planning baseline",
            source_version="Planning baseline",
            rationale="Use a standard emergency food energy baseline for early planning before local adjustments.",
            hazard_types=supported_hazards,
        ),
        AssumptionRecord(
            identifier="staffing.shift_hours_per_day",
            title="Usable staffing shift hours per operational day",
            category=AssumptionCategory.STAFFING,
            unit="hours/person/day",
            baseline_value=8.0,
            recommended_min=6.0,
            recommended_max=12.0,
            source_name="Operational staffing policy",
            source_version="Initial default",
            rationale="Provide a conservative staffing baseline for v1 role coverage calculations.",
            hazard_types=supported_hazards,
        ),
        AssumptionRecord(
            identifier="transport.reliability_buffer",
            title="Transport reliability buffer",
            category=AssumptionCategory.TRANSPORT,
            unit="ratio",
            baseline_value=0.85,
            recommended_min=0.6,
            recommended_max=0.95,
            source_name="Operational contingency policy",
            source_version="Initial default",
            rationale="Reduce nominal transport capacity to reflect breakdowns, route degradation, and delays.",
            hazard_types=supported_hazards,
            confidence_level=ConfidenceLevel.CONDITIONAL,
        ),
        AssumptionRecord(
            identifier="contingency.general_buffer_ratio",
            title="General contingency uplift",
            category=AssumptionCategory.CONTINGENCY,
            unit="ratio",
            baseline_value=0.15,
            recommended_min=0.05,
            recommended_max=0.3,
            source_name="Operational contingency policy",
            source_version="Initial default",
            rationale="Apply a transparent contingency margin to early planning scenarios.",
            hazard_types=supported_hazards,
            confidence_level=ConfidenceLevel.CONDITIONAL,
        ),
    )