from __future__ import annotations

from math import ceil

from engine.contracts import AssumptionIndex, TransportResult
from domain.models import Scenario


def compute_transport(scenario: Scenario, assumptions: AssumptionIndex) -> TransportResult:
    required_mass_kg = _resource_mass_kg(scenario)
    assumed_route_distance_km = _assumed_route_distance_km(scenario)

    available_capacity_kg = 0.0
    weighted_speed_sum = 0.0
    weighted_speed_count = 0.0
    daily_movable_capacity_kg = 0.0
    for asset in scenario.transportation:
        effective_capacity = (
            asset.capacity_kg
            * asset.quantity
            * max(min(asset.reliability_score, 1.0), 0.0)
            * assumptions.transport_reliability_buffer
        )
        available_capacity_kg += effective_capacity

        if asset.speed_kmh > 0 and asset.quantity > 0:
            weighted_speed_sum += asset.speed_kmh * asset.quantity
            weighted_speed_count += asset.quantity

            # One round trip uses travel time plus fixed loading/unloading handling.
            round_trip_hours = ((assumed_route_distance_km * 2) / asset.speed_kmh) + 2.0
            trips_per_day = max(0.5, min(24.0 / round_trip_hours, 6.0))
            daily_movable_capacity_kg += effective_capacity * trips_per_day

    average_speed_kmh = (weighted_speed_sum / weighted_speed_count) if weighted_speed_count > 0 else 0.0

    coverage = min(1.0, available_capacity_kg / required_mass_kg) if required_mass_kg else 1.0
    estimated_waves = (
        max(1, ceil(required_mass_kg / available_capacity_kg))
        if available_capacity_kg > 0 and required_mass_kg > 0
        else 0
    )
    estimated_delivery_days = (
        (required_mass_kg / daily_movable_capacity_kg)
        if daily_movable_capacity_kg > 0 and required_mass_kg > 0
        else 0.0
    )

    return TransportResult(
        required_mass_kg=required_mass_kg,
        available_capacity_kg=available_capacity_kg,
        coverage=coverage,
        estimated_waves=estimated_waves,
        estimated_delivery_days=estimated_delivery_days,
        daily_movable_capacity_kg=daily_movable_capacity_kg,
        average_speed_kmh=average_speed_kmh,
        assumed_route_distance_km=assumed_route_distance_km,
    )


def _resource_mass_kg(scenario: Scenario) -> float:
    total = 0.0
    for resource in scenario.resources:
        if resource.unit in {"kg", "liters"}:
            total += resource.quantity
    return total


def _assumed_route_distance_km(scenario: Scenario) -> float:
    road_access = max(0.0, min(scenario.infrastructure_profile.road_access_score, 1.0))
    # Lower access score implies detours and degraded route conditions.
    return 120.0 * (1.0 + (1.0 - road_access))
