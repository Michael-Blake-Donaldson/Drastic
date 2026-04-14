from __future__ import annotations
from dataclasses import dataclass, field, replace
from typing import Any, List, Dict, Tuple
from domain.models import Scenario, AnalysisSummary, InventoryPosition, PersonnelRole, TransportAsset

@dataclass(frozen=True)
class DailyResourceState:
    name: str
    category: str
    starting: float
    delivered: float
    consumed: float
    remaining: float
    unit: str
    notes: str = ""

@dataclass(frozen=True)
class DailyPersonnelState:
    name: str
    starting: int
    deployed: int
    exhausted: int
    available: int
    notes: str = ""

@dataclass(frozen=True)
class DailyTransportState:
    name: str
    starting: int
    in_use: int
    idle: int
    breakdowns: int
    arrivals: int
    notes: str = ""

@dataclass(frozen=True)
class DailyEvent:
    code: str
    description: str
    details: str = ""

@dataclass(frozen=True)
class DailySimulationState:
    day: int
    resources: Tuple[DailyResourceState, ...]
    personnel: Tuple[DailyPersonnelState, ...]
    transport: Tuple[DailyTransportState, ...]
    unmet_needs: Tuple[str, ...]
    risk_flags: Tuple[str, ...]
    events: Tuple[DailyEvent, ...]


def project_simulation_timeline(
    scenario: Scenario,
    analysis: AnalysisSummary,
    days: int | None = None,
) -> List[DailySimulationState]:
    """
    Projects the scenario state for each day, returning a list of DailySimulationState.
    This is a simplified placeholder; real logic should model resource delivery, consumption, personnel fatigue, etc.
    """
    duration = days or scenario.hazard_profile.duration_days
    timeline: List[DailySimulationState] = []

    # --- Assumptions and local supply ---
    # Sphere/assumption baselines (hardcoded for now, could be loaded dynamically)
    SPHERE_BASELINES = {
        "water": 15.0,  # liters/person/day
        "food": 2100.0, # kcal/person/day
        "shelter": 3.5, # m2/person (example)
        # Add more as needed
    }

    pop = scenario.population_profile
    infra = scenario.infrastructure_profile
    hazard = scenario.hazard_profile

    # Local supply factors (from infrastructure/geography)
    local_supply = {
        "water": getattr(infra, "local_water_availability_liters_per_day", 0.0),
        "food": getattr(infra, "local_food_supply_ratio", 0.0),
        # Add more as needed
    }

    # Infrastructure/road/transport factors
    road_access = getattr(infra, "road_access_score", 1.0)
    infra_damage = getattr(hazard, "infrastructure_damage_percent", 0.0) / 100.0

    # Initial values
    resource_states = [
        dict(
            name=pos.name,
            category=pos.category,
            starting=pos.quantity,
            delivered=0.0,
            consumed=0.0,
            remaining=pos.quantity,
            unit=pos.unit,
            notes=""
        )
        for pos in scenario.resources
    ]
    personnel_states = [
        dict(
            name=role.name,
            starting=role.count,
            deployed=0,
            exhausted=0,
            available=role.count,
            notes=""
        )
        for role in scenario.personnel
    ]
    transport_states = [
        dict(
            name=asset.name,
            starting=asset.quantity,
            in_use=0,
            idle=asset.quantity,
            breakdowns=0,
            arrivals=0,
            reliability=getattr(asset, "reliability_score", 0.85),
            capacity=getattr(asset, "capacity_kg", 0.0),
            notes=""
        )
        for asset in scenario.transportation
    ]

    for day in range(1, duration + 1):
        events = []
        # --- Resource loop ---
        for r in resource_states:
            # Determine baseline need per day for this resource
            cat = r["category"].lower()
            if cat in SPHERE_BASELINES:
                if cat == "water":
                    daily_need = SPHERE_BASELINES[cat] * pop.total_population
                    local_avail = local_supply["water"]
                elif cat == "food":
                    daily_need = SPHERE_BASELINES[cat] * pop.total_population
                    local_avail = local_supply["food"] * daily_need  # ratio * need
                else:
                    daily_need = SPHERE_BASELINES[cat] * pop.total_population
                    local_avail = 0.0
            else:
                daily_need = r["starting"] / duration if duration > 0 else 0
                local_avail = 0.0

            # Local supply offsets need
            local_used = min(local_avail, daily_need)
            remaining_need = daily_need - local_used

            # Delivery is affected by road access, infra damage, and transport reliability
            # Assume all transport assets are pooled for delivery
            total_transport_capacity = sum(
                t["capacity"] * t["starting"] * t["reliability"] for t in transport_states
            )
            # Delivery efficiency drops with infra damage and road access
            delivery_efficiency = max(0.1, road_access * (1.0 - infra_damage))
            delivered = min(remaining_need, total_transport_capacity * delivery_efficiency)

            # Consumption is the minimum of what's available and what's needed
            consumed = min(r["remaining"] + delivered, daily_need)
            r["delivered"] += delivered
            r["consumed"] += consumed
            r["remaining"] = max(0.0, r["remaining"] + delivered - consumed)

            # Event: local supply exhausted
            if local_avail > 0 and local_used >= local_avail:
                events.append(DailyEvent(
                    code=f"{cat}_local_supply_exhausted",
                    description=f"Local {cat} supply exhausted",
                    details=f"Local supply met {local_avail:.1f} units on day {day}"
                ))
                local_supply[cat] = 0.0

            # Event: resource running low
            if r["remaining"] < daily_need * 0.5:
                events.append(DailyEvent(
                    code="resource_low",
                    description=f"{r['name']} running low",
                    details=f"{r['remaining']:.1f} {r['unit']} left"
                ))

            # Event: unmet need
            if consumed < daily_need:
                events.append(DailyEvent(
                    code="unmet_need",
                    description=f"Unmet {r['name']} need",
                    details=f"{daily_need - consumed:.1f} {r['unit']} unmet on day {day}"
                ))

        # --- Personnel: fatigue model ---
        for p in personnel_states:
            deployed = int(p["starting"] * 0.7)
            exhausted = int((day / duration) * deployed)
            available = max(0, p["starting"] - deployed - exhausted)
            p["deployed"] = deployed
            p["exhausted"] = exhausted
            p["available"] = available
            if exhausted > 0 and day % 3 == 0:
                events.append(DailyEvent(
                    code="personnel_fatigue",
                    description=f"{p['name']} fatigue",
                    details=f"{exhausted} exhausted"
                ))

        # --- Transport: breakdown model ---
        for t in transport_states:
            in_use = int(t["starting"] * 0.6)
            breakdowns = 1 if day % 5 == 0 else 0
            idle = max(0, t["starting"] - in_use - breakdowns)
            arrivals = 1 if day == 1 else 0
            t["in_use"] = in_use
            t["breakdowns"] = breakdowns
            t["idle"] = idle
            t["arrivals"] = arrivals
            if breakdowns:
                events.append(DailyEvent(
                    code="transport_breakdown",
                    description=f"{t['name']} breakdown",
                    details=f"{breakdowns} asset(s) affected"
                ))

        # Unmet needs and risk flags (placeholder: static from analysis)
        unmet_needs = analysis.unmet_critical_needs if day == duration else ()
        risk_flags = tuple(flag.title for flag in analysis.risk_flags) if day == duration else ()
        # Only pass fields accepted by DailyTransportState
        def filter_transport_fields(t):
            allowed = {"name", "starting", "in_use", "idle", "breakdowns", "arrivals", "notes"}
            return {k: v for k, v in t.items() if k in allowed}

        timeline.append(DailySimulationState(
            day=day,
            resources=tuple(DailyResourceState(**r) for r in resource_states),
            personnel=tuple(DailyPersonnelState(**p) for p in personnel_states),
            transport=tuple(DailyTransportState(**filter_transport_fields(t)) for t in transport_states),
            unmet_needs=unmet_needs,
            risk_flags=risk_flags,
            events=tuple(events),
        ))
    return timeline
