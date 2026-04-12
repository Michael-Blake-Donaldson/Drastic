from __future__ import annotations

from math import ceil

from engine.contracts import AssumptionIndex, TransportResult
from domain.models import Scenario


def compute_transport(scenario: Scenario, assumptions: AssumptionIndex) -> TransportResult:
    required_mass_kg = _resource_mass_kg(scenario)

    available_capacity_kg = 0.0
    for asset in scenario.transportation:
        available_capacity_kg += (
            asset.capacity_kg
            * asset.quantity
            * max(min(asset.reliability_score, 1.0), 0.0)
            * assumptions.transport_reliability_buffer
        )

    coverage = min(1.0, available_capacity_kg / required_mass_kg) if required_mass_kg else 1.0
    estimated_waves = (
        max(1, ceil(required_mass_kg / available_capacity_kg))
        if available_capacity_kg > 0 and required_mass_kg > 0
        else 0
    )

    return TransportResult(
        required_mass_kg=required_mass_kg,
        available_capacity_kg=available_capacity_kg,
        coverage=coverage,
        estimated_waves=estimated_waves,
    )


def _resource_mass_kg(scenario: Scenario) -> float:
    total = 0.0
    for resource in scenario.resources:
        if resource.unit in {"kg", "liters"}:
            total += resource.quantity
    return total
