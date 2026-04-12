from __future__ import annotations

import unittest

from domain.enums import ConfidenceLevel, HazardType, ScenarioStatus
from domain.models import AnalysisSummary, HazardProfile, InfrastructureProfile, PopulationProfile, Scenario
from services.report_templates import build_scenario_report


class ScenarioReportTests(unittest.TestCase):
    def _scenario(self) -> Scenario:
        return Scenario(
            scenario_id="scenario-a",
            project_id="project-1",
            name="Scenario A",
            status=ScenarioStatus.DRAFT,
            hazard_profile=HazardProfile(
                hazard_type=HazardType.FLOOD,
                severity_band="high",
                duration_days=14,
                location_label="USA / Florida",
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
            world_region="North America",
            country="USA",
            region="Florida",
            latitude=27.6648,
            longitude=-81.5158,
        )

    def _analysis(self) -> AnalysisSummary:
        return AnalysisSummary(
            critical_coverage_percent=80.0,
            overall_coverage_percent=74.0,
            total_estimated_cost=100000.0,
            confidence_level=ConfidenceLevel.BASELINE,
            unmet_critical_needs=("water",),
            assumptions_trace=("assumption.transport.speed",),
            metadata={
                "transport_estimated_waves": 2,
                "transport_mass_required_kg": 30000.0,
            },
        )

    def test_scenario_report_includes_map_context_and_timeline_day(self) -> None:
        report = build_scenario_report(self._scenario(), self._analysis(), timeline_day=6)

        self.assertIn("Map Simulation Context", report)
        self.assertIn("- World region: North America", report)
        self.assertIn("- Latitude: 27.6648", report)
        self.assertIn("- Longitude: -81.5158", report)
        self.assertIn("- Timeline day snapshot: 6", report)


if __name__ == "__main__":
    unittest.main()
