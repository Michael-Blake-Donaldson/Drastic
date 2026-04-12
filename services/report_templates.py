from __future__ import annotations

from datetime import datetime

from domain.models import AnalysisSummary, Scenario


def build_scenario_report(scenario: Scenario, analysis: AnalysisSummary) -> str:
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
    winner: str,
    lineage_left: str,
    lineage_right: str,
) -> str:
    lines = [
        "DRASTIC Comparison Report",
        f"Generated: {datetime.now().isoformat(timespec='seconds')}",
        "",
        "Comparison Configuration",
        f"- Profile: {profile}",
        f"- Scenario A: {left_scenario.name} [{left_scenario.variant_label}]",
        f"- Scenario B: {right_scenario.name} [{right_scenario.variant_label}]",
        f"- Lineage A: {lineage_left}",
        f"- Lineage B: {lineage_right}",
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
        "",
        "Unmet Needs A",
    ]

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