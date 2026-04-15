# Phase 1 Foundation Baseline (Completed)

Date: 2026-04-14
Scope: Foundation and baseline only (no async execution model changes yet)

## 1. Objectives Completed

1. Defined measurable performance targets and acceptance thresholds.
2. Added safe profiling checkpoints in analysis, comparison, and map refresh flows.
3. Centralized UI design tokens and stylesheet for maintainable modernization.
4. Established accessibility and keyboard readiness baseline checklist.
5. Produced a prioritized implementation backlog for Phase 2+.

## 2. Performance Targets (Baseline Guardrails)

These are practical release guardrails for desktop operation on representative hardware:

1. Analysis action responsiveness
- P50 total analysis action latency: <= 250 ms
- P95 total analysis action latency: <= 750 ms

2. Comparison action responsiveness (two scenarios analyzed)
- P50 comparison latency: <= 600 ms
- P95 comparison latency: <= 1500 ms

3. Map refresh responsiveness
- P50 map refresh latency: <= 100 ms
- P95 map refresh latency: <= 250 ms

4. UI responsiveness
- Main UI interaction should remain non-blocking for pointer/keyboard input while long operations run (enforced in Phase 2 via worker threading).

## 3. Instrumentation Added

Structured NDJSON performance telemetry is now written to:
- %APPDATA%/Drastic/logs/performance.ndjson

Event schema:
- timestamp_utc: ISO-8601 UTC
- event: short identifier
- duration_ms: float (rounded)
- details: bounded, sanitized primitive payload

Current events:
- analysis_run_total
- analysis_load_total
- comparison_total
- map_refresh_total

Engine metadata now includes module-level timing keys:
- perf_needs_ms
- perf_staffing_ms
- perf_transport_ms
- perf_costs_ms
- perf_total_analyze_ms

Security and privacy posture:
- No raw free-form notes or full user-entered text is persisted by telemetry.
- Detail values are bounded and normalized before write.
- Logging failures do not interrupt user workflow.

## 4. UI Design Foundation Added

Theme system foundation introduced:
- ui/theme.py

Delivered:
- Theme token model (font family and base size)
- Centralized APP_STYLESHEET source
- Main window now consumes shared theme source instead of inline large stylesheet block

Benefit:
- Lower risk UI refactors in future phases
- Easier high-DPI and contrast evolution without editing large UI classes

## 5. Accessibility Baseline Checklist (Phase 1 Audit)

Status legend:
- DONE: implemented in codebase
- NEXT: planned in next phase

Checklist:
1. Core action discoverability via toolbar action labels and status tips: DONE
2. Clear validation message surface (banner + dialog): DONE
3. Centralized theme for consistent focus/error styling updates: DONE
4. Keyboard shortcuts for critical actions (run/save/export/tab switching): NEXT
5. Explicit accessible names/descriptions for key widgets: NEXT
6. Tab order verification and keyboard-only workflow test pass: NEXT
7. Contrast verification against WCAG guidance: NEXT
8. Screen-reader smoke test (Narrator): NEXT

## 6. Prioritized Backlog (Next Phases)

Priority P0 (next):
1. Move analysis/comparison execution off UI thread (QThread worker model)
2. Add cancellation and progress reporting for long-running operations
3. Add user-safe error surfacing for worker exceptions

Priority P1:
1. Keyboard shortcuts and visible shortcut hints in tooltips/menu labels
2. Explicit accessibility metadata and tab-order hardening
3. High-DPI and responsive layout validation matrix (100/125/150/200%)

Priority P2:
1. OpenStreetMap integration via QWebEngineView + Leaflet
2. Layered map overlays and timeline-aware rendering diffs
3. Performance-optimized marker updates for large scenarios

## 7. Phase 1 Exit Criteria

Phase 1 is considered complete because:
1. Baseline observability is present and persistent.
2. Timing checkpoints cover known heavy user flows.
3. Styling is centralized for maintainable modernization.
4. Accessibility baseline and prioritized backlog are documented.

## 8. Operational Guidance

Use this command to inspect telemetry quickly in PowerShell:

Get-Content "$env:APPDATA\Drastic\logs\performance.ndjson" -Tail 20

Recommended baseline capture process before Phase 2:
1. Launch app and run 10 analysis actions across small/medium/large scenarios.
2. Run at least 5 scenario comparisons.
3. Interact with timeline and map controls for at least 20 refreshes.
4. Compute P50/P95 from NDJSON and compare with guardrails above.
