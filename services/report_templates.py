from __future__ import annotations

from datetime import datetime

from domain.models import AnalysisSummary, Scenario


def build_scenario_report(
    scenario: Scenario,
    analysis: AnalysisSummary,
    timeline_day: int | None = None,
) -> str:
    lines = [
        "DRASTIC Scenario Report",
        f"Generated: {datetime.now().isoformat(timespec='seconds')}",
        "",
        "Scenario Context",
        f"- Name: {scenario.name}",
        f"- Variant: {scenario.variant_label}",
        f"- Status: {scenario.status.value}",
        f"- Hazard: {scenario.hazard_profile.hazard_type.value}",
        f"- Severity: {scenario.hazard_profile.severity_band}",
        f"- Location: {scenario.hazard_profile.location_label}",
        f"- Duration days: {scenario.hazard_profile.duration_days}",
        f"- Base scenario id: {scenario.base_scenario_id or 'None'}",
        f"- Lineage summary: {'Root baseline' if scenario.base_scenario_id is None else f'Variant of {scenario.base_scenario_id}'}",
        "",
        "Map Simulation Context",
        f"- World region: {scenario.world_region or 'n/a'}",
        f"- Country: {scenario.country or 'n/a'}",
        f"- Region: {scenario.region or 'n/a'}",
        f"- Latitude: {_format_coord(scenario.latitude)}",
        f"- Longitude: {_format_coord(scenario.longitude)}",
        f"- Timeline day snapshot: {timeline_day if timeline_day is not None else 1}",
        "",
        "Planning Summary",
        f"- Critical coverage: {analysis.critical_coverage_percent}%",
        f"- Overall coverage: {analysis.overall_coverage_percent}%",
        f"- Estimated total cost: ${analysis.total_estimated_cost:,.2f}",
        f"- Confidence: {analysis.confidence_level.value}",
        "",
        "Operational Scheduling",
        f"- Estimated transport waves: {analysis.metadata.get('transport_estimated_waves', 'n/a')}",
        f"- Required transport mass kg: {analysis.metadata.get('transport_mass_required_kg', 'n/a')}",
        f"- Available transport capacity kg: {analysis.metadata.get('transport_capacity_kg', 'n/a')}",
        f"- Estimated delivery days: {analysis.metadata.get('transport_estimated_delivery_days', 'n/a')}",
        f"- Daily movable capacity kg: {analysis.metadata.get('transport_daily_movable_capacity_kg', 'n/a')}",
        f"- Assumed route distance km: {analysis.metadata.get('transport_assumed_route_distance_km', 'n/a')}",
        f"- Average transport speed km/h: {analysis.metadata.get('transport_average_speed_kmh', 'n/a')}",
        "",
        "Unmet Critical Needs",
    ]

    if analysis.unmet_critical_needs:
        lines.extend(f"- {item}" for item in analysis.unmet_critical_needs)
    else:
        lines.append("- None")

    lines.extend(
        [
            "",
            "Risk Flags",
        ]
    )

    if analysis.risk_flags:
        lines.extend(f"- {flag.title}: {flag.detail}" for flag in analysis.risk_flags)
    else:
        lines.append("- None")

    lines.extend(
        [
            "",
            "Computed Metrics",
        ]
    )
    for key, value in analysis.metadata.items():
        lines.append(f"- {key}: {value}")

    lines.extend(
        [
            "",
            "Assumptions Trace",
        ]
    )
    lines.extend(f"- {identifier}" for identifier in analysis.assumptions_trace)
    return "\n".join(lines)


def build_comparison_report(
    left_scenario: Scenario,
    right_scenario: Scenario,
    left_analysis: AnalysisSummary,
    right_analysis: AnalysisSummary,
    profile: str,
    profile_weights: dict[str, float],
    metric_filter: str,
    winner: str,
    lineage_left: str,
    lineage_right: str,
    timeline_day: int | None = None,
) -> str:
    lines = [
        "DRASTIC Comparison Report",
        f"Generated: {datetime.now().isoformat(timespec='seconds')}",
        "",
        "Comparison Configuration",
        f"- Profile: {profile}",
        f"- Profile weights: {profile_weights}",
        f"- Metric filter: {metric_filter}",
        f"- Scenario A: {left_scenario.name} [{left_scenario.variant_label}]",
        f"- Scenario B: {right_scenario.name} [{right_scenario.variant_label}]",
        f"- Lineage A: {lineage_left}",
        f"- Lineage B: {lineage_right}",
        f"- Timeline day snapshot: {timeline_day if timeline_day is not None else 1}",
        "",
        "Map Context A",
        f"- World region: {left_scenario.world_region or 'n/a'}",
        f"- Country: {left_scenario.country or 'n/a'}",
        f"- Region: {left_scenario.region or 'n/a'}",
        f"- Latitude: {_format_coord(left_scenario.latitude)}",
        f"- Longitude: {_format_coord(left_scenario.longitude)}",
        "",
        "Map Context B",
        f"- World region: {right_scenario.world_region or 'n/a'}",
        f"- Country: {right_scenario.country or 'n/a'}",
        f"- Region: {right_scenario.region or 'n/a'}",
        f"- Latitude: {_format_coord(right_scenario.latitude)}",
        f"- Longitude: {_format_coord(right_scenario.longitude)}",
        "",
        "Top-Level Deltas (B - A)",
        f"- Critical coverage delta: {right_analysis.critical_coverage_percent - left_analysis.critical_coverage_percent:+.1f}%",
        f"- Overall coverage delta: {right_analysis.overall_coverage_percent - left_analysis.overall_coverage_percent:+.1f}%",
        f"- Total estimated cost delta: ${right_analysis.total_estimated_cost - left_analysis.total_estimated_cost:+,.2f}",
        f"- Winner: {winner}",
        "",
        "Operational Scheduling Deltas",
        f"- Transport wave delta: {_metric_delta(right_analysis, left_analysis, 'transport_estimated_waves')}",
        f"- Transport mass delta: {_metric_delta(right_analysis, left_analysis, 'transport_mass_required_kg')}",
        f"- Transport capacity delta: {_metric_delta(right_analysis, left_analysis, 'transport_capacity_kg')}",
        f"- Estimated delivery days delta: {_metric_delta(right_analysis, left_analysis, 'transport_estimated_delivery_days')}",
        f"- Daily movable capacity delta: {_metric_delta(right_analysis, left_analysis, 'transport_daily_movable_capacity_kg')}",
        f"- Assumed route distance delta: {_metric_delta(right_analysis, left_analysis, 'transport_assumed_route_distance_km')}",
        f"- Average speed delta: {_metric_delta(right_analysis, left_analysis, 'transport_average_speed_kmh')}",
        "",
        "Detailed Metric Deltas",
        "",
        "Unmet Needs A",
    ]

    deltas = filtered_metric_deltas(left_analysis.metadata, right_analysis.metadata, metric_filter)
    if deltas:
        for key, delta in deltas:
            lines.append(f"- {key}: {delta:+.2f}")
    else:
        lines.append("- No numeric metrics matched the selected filter.")
    lines.append("")

    if left_analysis.unmet_critical_needs:
        lines.extend(f"- {item}" for item in left_analysis.unmet_critical_needs)
    else:
        lines.append("- None")

    lines.extend(["", "Unmet Needs B"])
    if right_analysis.unmet_critical_needs:
        lines.extend(f"- {item}" for item in right_analysis.unmet_critical_needs)
    else:
        lines.append("- None")

    lines.extend(["", "Assumptions Trace A"])
    lines.extend(f"- {identifier}" for identifier in left_analysis.assumptions_trace)
    lines.extend(["", "Assumptions Trace B"])
    lines.extend(f"- {identifier}" for identifier in right_analysis.assumptions_trace)

    return "\n".join(lines)


def _metric_delta(right_analysis: AnalysisSummary, left_analysis: AnalysisSummary, key: str) -> str:
    right_value = right_analysis.metadata.get(key)
    left_value = left_analysis.metadata.get(key)
    if isinstance(right_value, (int, float)) and isinstance(left_value, (int, float)):
        return f"{right_value - left_value:+.2f}"
    return "n/a"


def _format_coord(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.4f}"


def filtered_metric_deltas(
    left_metadata: dict[str, object],
    right_metadata: dict[str, object],
    metric_filter: str,
) -> list[tuple[str, float]]:
    shared_keys = sorted(set(left_metadata).intersection(right_metadata))
    deltas: list[tuple[str, float]] = []
    for key in shared_keys:
        left_value = left_metadata[key]
        right_value = right_metadata[key]
        if not isinstance(left_value, (int, float)) or not isinstance(right_value, (int, float)):
            continue
        if not matches_metric_filter(key, metric_filter):
            continue
        deltas.append((key, float(right_value - left_value)))
    return deltas


def matches_metric_filter(key: str, selected_filter: str) -> bool:
    if selected_filter == "All Metrics":
        return True
    category = metric_category(key)
    if selected_filter == "Coverage":
        return category == "Coverage"
    if selected_filter == "Cost":
        return category == "Cost"
    if selected_filter == "Staffing":
        return category == "Staffing"
    if selected_filter == "Transport":
        return category == "Transport"
    return True


def metric_category(key: str) -> str:
    if key.startswith("transport_"):
        return "Transport"
    if key.startswith("personnel_") or "staff" in key:
        return "Staffing"
    if key.startswith("cost_") or key.endswith("_cost") or "cost" in key:
        return "Cost"
    if "coverage" in key:
        return "Coverage"
    return "Other"