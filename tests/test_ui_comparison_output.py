from __future__ import annotations

import unittest

from domain.enums import ConfidenceLevel, HazardType, ScenarioStatus
from domain.models import AnalysisSummary, HazardProfile, InfrastructureProfile, PopulationProfile, Scenario
from ui.main_window import build_comparison_output_text


class UIComparisonOutputTests(unittest.TestCase):
    def _scenario(self, scenario_id: str, name: str, variant_label: str) -> Scenario:
        return Scenario(
            scenario_id=scenario_id,
            project_id="project-1",
            name=name,
            status=ScenarioStatus.DRAFT,
            hazard_profile=HazardProfile(
                hazard_type=HazardType.FLOOD,
                severity_band="high",
                duration_days=14,
                location_label="Test Location",
                infrastructure_damage_percent=35.0,
            ),
            population_profile=PopulationProfile(
                total_population=10000,
                displaced_population=2000,
            ),
            infrastructure_profile=InfrastructureProfile(
                road_access_score=0.6,
                health_facility_operability_score=0.7,
                local_water_availability_liters_per_day=1.2,
                local_food_supply_ratio=0.5,
            ),
            variant_label=variant_label,
            base_scenario_id=None,
        )

    def _analysis(self, critical: float, overall: float, cost: float, metadata: dict[str, float]) -> AnalysisSummary:
        return AnalysisSummary(
            critical_coverage_percent=critical,
            overall_coverage_percent=overall,
            total_estimated_cost=cost,
            confidence_level=ConfidenceLevel.BASELINE,
            unmet_critical_needs=(),
            assumptions_trace=("assumption.transport.speed",),
            metadata=metadata,
        )

    def test_build_output_shows_no_match_fallback_for_staffing_filter(self) -> None:
        left_scenario = self._scenario("scenario-a", "Scenario A", "baseline")
        right_scenario = self._scenario("scenario-b", "Scenario B", "branch")

        left_analysis = self._analysis(
            critical=78.0,
            overall=74.0,
            cost=120000.0,
            metadata={
                "transport_estimated_delivery_days": 4.0,
                "cost_total": 120000.0,
            },
        )
        right_analysis = self._analysis(
            critical=82.0,
            overall=79.0,
            cost=130000.0,
            metadata={
                "transport_estimated_delivery_days": 6.0,
                "cost_total": 130000.0,
            },
        )

        text = build_comparison_output_text(
            left_scenario=left_scenario,
            right_scenario=right_scenario,
            left_analysis=left_analysis,
            right_analysis=right_analysis,
            profile="Balanced",
            profile_weights={"critical": 2.0, "overall": 1.0, "cost": 0.0001},
            metric_filter="Staffing",
            winner="Scenario B leads selected metrics.",
            lineage_left="Scenario A [baseline]",
            lineage_right="Scenario A [baseline] -> Scenario B [branch]",
        )

        self.assertIn("Metric filter: Staffing", text)
        self.assertIn("Detailed metric deltas:", text)
        self.assertIn("- No numeric metrics matched the selected filter.", text)


if __name__ == "__main__":
    unittest.main()
