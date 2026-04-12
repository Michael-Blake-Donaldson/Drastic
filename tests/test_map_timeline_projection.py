from __future__ import annotations

import unittest

from domain.enums import ConfidenceLevel, HazardType, ScenarioStatus
from domain.models import AnalysisSummary, HazardProfile, InfrastructureProfile, PopulationProfile, Scenario
from ui.main_window import build_timeline_projection_lines


class MapTimelineProjectionTests(unittest.TestCase):
    def _scenario(self, duration_days: int) -> Scenario:
        return Scenario(
            scenario_id="scenario-a",
            project_id="project-1",
            name="Scenario A",
            status=ScenarioStatus.DRAFT,
            hazard_profile=HazardProfile(
                hazard_type=HazardType.FLOOD,
                severity_band="high",
                duration_days=duration_days,
                location_label="USA / Florida",
                infrastructure_damage_percent=35.0,
            ),
            population_profile=PopulationProfile(
                total_population=100000,
                displaced_population=20000,
            ),
            infrastructure_profile=InfrastructureProfile(
                road_access_score=0.6,
                health_facility_operability_score=0.7,
                local_water_availability_liters_per_day=400000.0,
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
            critical_coverage_percent=84.0,
            overall_coverage_percent=76.0,
            total_estimated_cost=1200000.0,
            confidence_level=ConfidenceLevel.BASELINE,
            unmet_critical_needs=("water", "shelter"),
            assumptions_trace=("assumption.transport.speed",),
            metadata={
                "transport_estimated_delivery_days": 6.0,
                "transport_daily_movable_capacity_kg": 24000.0,
            },
        )

    def test_projection_lines_include_transport_fields_when_present(self) -> None:
        lines = build_timeline_projection_lines(self._scenario(duration_days=10), self._analysis(), day=4)
        rendered = "\n".join(lines)

        self.assertIn("Timeline Day 4/10", rendered)
        self.assertIn("Estimated delivery ETA remaining:", rendered)
        self.assertIn("Projected tonnage moved:", rendered)

    def test_projection_lines_clamp_day_to_duration(self) -> None:
        lines = build_timeline_projection_lines(self._scenario(duration_days=5), self._analysis(), day=99)

        self.assertEqual(lines[0], "Timeline Day 5/5")


if __name__ == "__main__":
    unittest.main()
