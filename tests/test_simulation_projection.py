from __future__ import annotations
import unittest
from domain.enums import ConfidenceLevel, ScenarioStatus, HazardType
from domain.models import Scenario, HazardProfile, PopulationProfile, InfrastructureProfile, InventoryPosition, PersonnelRole, TransportAsset, AnalysisSummary
from engine.simulation import project_simulation_timeline

class SimulationProjectionTests(unittest.TestCase):
    def _scenario(self) -> Scenario:
        return Scenario(
            scenario_id="s1",
            project_id="p1",
            name="Test Scenario",
            status=ScenarioStatus.DRAFT,
            hazard_profile=HazardProfile(
                hazard_type=HazardType.FLOOD,
                severity_band="high",
                duration_days=5,
                location_label="USA / Florida",
                infrastructure_damage_percent=30.0,
            ),
            population_profile=PopulationProfile(
                total_population=10000,
                displaced_population=2000,
            ),
            infrastructure_profile=InfrastructureProfile(
                road_access_score=0.7,
                health_facility_operability_score=0.8,
                local_water_availability_liters_per_day=100000.0,
                local_food_supply_ratio=0.6,
            ),
            resources=(
                InventoryPosition(name="Water", category="water", quantity=5000.0, unit="liters", priority_rank=1),
                InventoryPosition(name="Food", category="food", quantity=3000.0, unit="kg", priority_rank=1),
            ),
            personnel=(
                PersonnelRole(name="Medic", count=10, shift_hours=8, hourly_cost=20.0),
            ),
            transportation=(
                TransportAsset(name="Truck", capacity_kg=2000.0, quantity=3, speed_kmh=40.0, reliability_score=0.9, cost_per_km=2.0),
            ),
        )

    def _analysis(self) -> AnalysisSummary:
        return AnalysisSummary(
            critical_coverage_percent=80.0,
            overall_coverage_percent=70.0,
            total_estimated_cost=100000.0,
            confidence_level=ConfidenceLevel.BASELINE,
            unmet_critical_needs=("water",),
            risk_flags=(),
            assumptions_trace=("assumption.transport.speed",),
            metadata={}
        )

    def test_projection_length_and_day_numbers(self):
        scenario = self._scenario()
        analysis = self._analysis()
        timeline = project_simulation_timeline(scenario, analysis)
        self.assertEqual(len(timeline), scenario.hazard_profile.duration_days)
        self.assertEqual(timeline[0].day, 1)
        self.assertEqual(timeline[-1].day, scenario.hazard_profile.duration_days)

    def test_resource_depletion_and_events(self):
        scenario = self._scenario()
        analysis = self._analysis()
        timeline = project_simulation_timeline(scenario, analysis)
        # Water should decrease, and at some point trigger a low event
        water_states = [day.resources[0] for day in timeline]
        self.assertTrue(any(ev.code == "resource_low" for day in timeline for ev in day.events))
        self.assertTrue(all(water_states[i].remaining >= water_states[i+1].remaining for i in range(len(water_states)-1)))

    def test_personnel_fatigue_and_events(self):
        scenario = self._scenario()
        analysis = self._analysis()
        timeline = project_simulation_timeline(scenario, analysis)
        # Fatigue event should occur on day 3
        fatigue_days = [day for day in timeline if any(ev.code == "personnel_fatigue" for ev in day.events)]
        self.assertTrue(any(day.day == 3 for day in fatigue_days))

    def test_transport_breakdown_and_events(self):
        scenario = self._scenario()
        analysis = self._analysis()
        timeline = project_simulation_timeline(scenario, analysis)
        # Breakdown event should occur on day 5
        breakdown_days = [day for day in timeline if any(ev.code == "transport_breakdown" for ev in day.events)]
        self.assertTrue(any(day.day == 5 for day in breakdown_days))

    def test_unmet_needs_and_risk_flags_on_last_day(self):
        scenario = self._scenario()
        analysis = self._analysis()
        timeline = project_simulation_timeline(scenario, analysis)
        self.assertEqual(timeline[-1].unmet_needs, analysis.unmet_critical_needs)
        self.assertEqual(timeline[-1].risk_flags, ())
        self.assertEqual(timeline[0].unmet_needs, ())

if __name__ == "__main__":
    unittest.main()
