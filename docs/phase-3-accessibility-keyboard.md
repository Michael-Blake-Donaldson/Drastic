# Phase 3 — Accessibility & Keyboard Hardening

**Status:** Complete  
**Tests:** 19 / 19 passing  
**Files modified:** `ui/main_window.py`, `app/bootstrap.py`

---

## Objectives

- Full keyboard access to every critical workflow without requiring a mouse
- Screen-reader compatibility via explicit accessible names on all interactive widgets
- Informative tooltips on every form input and button
- Correct fractional-DPI rendering at 125 %, 150 %, and 200 % scale factors

---

## 1. Keyboard Shortcuts

All primary toolbar actions now carry `QKeySequence` shortcuts registered on the `QAction`
objects (context: `Qt::WindowShortcut`).

| Action | Shortcut |
|---|---|
| New Scenario | `Ctrl+N` |
| Save Scenario | `Ctrl+S` |
| Run Analysis | `Ctrl+R` |
| Cancel Task | `Escape` |
| Branch Variant | `Ctrl+B` |
| Compare Variants | `Ctrl+M` |
| Export | `Ctrl+E` |
| Switch to Scenario tab | `Ctrl+1` |
| Switch to Assumptions tab | `Ctrl+2` |
| Switch to Results tab | `Ctrl+3` |
| Switch to Map Simulation tab | `Ctrl+4` |
| Switch to Compare tab | `Ctrl+5` |

Tab-switch shortcuts are registered as window-level `QAction` objects added via
`self.addAction()` so they fire regardless of which widget has focus.

---

## 2. Accessible Names

Every interactive widget now has `.setAccessibleName()` set to a human-readable label
that matches the visible form row label. Screen readers (Narrator, NVDA) announce these
when focus moves to the widget.

**Scenario editor form:** `name_input`, `world_region_combo`, `country_combo`,
`region_combo`, `latitude_input`, `longitude_input`, `hazard_combo`, `severity_input`,
`duration_input`, `infrastructure_damage_input`, `total_population_input`,
`displaced_population_input`, `children_input`, `older_adults_input`, `pregnant_input`,
`medically_vulnerable_input`, `road_access_input`, `health_operability_input`,
`water_availability_input`, `food_supply_ratio_input`, `notes_input`, `save_button`,
`analyze_button`, `preview_button`

**Left navigation panel:** `scenario_search_input`, `scenario_status_filter_combo`,
`scenario_list_widget`

**Compare tab:** `compare_left_combo`, `compare_right_combo`, `comparison_profile_combo`,
`metric_filter_combo`, `run_compare_button`, `copy_compare_button`, `swap_button`,
`export_compare_button`

**Workspace tab widget:** `setAccessibleName("Workspace Tabs")`

---

## 3. Tooltips

Every widget with an accessible name also has a matching `.setToolTip()` that describes:
- What the field controls
- Valid value range where applicable (e.g., "0.0 = fully blocked, 1.0 = fully open")
- The keyboard shortcut where relevant (e.g., "Ctrl+R" on **Analyze Scenario** button)

---

## 4. Tab Order

`_setup_tab_order()` is called at the end of `__init__` after all widgets are constructed.
It chains `QWidget.setTabOrder(first, second)` across the full logical sequence:

```
scenario_search_input → scenario_status_filter_combo → scenario_list_widget
→ name_input → world_region_combo → country_combo → region_combo
→ latitude_input → longitude_input → hazard_combo → severity_input → duration_input
→ infrastructure_damage_input → total_population_input → displaced_population_input
→ children_input → older_adults_input → pregnant_input → medically_vulnerable_input
→ road_access_input → health_operability_input → water_availability_input
→ food_supply_ratio_input → notes_input → save_button → analyze_button
```

---

## 5. High-DPI Scaling

`app/bootstrap.py` sets the rounding policy **before** `QApplication` is constructed:

```python
QApplication.setHighDpiScaleFactorRoundingPolicy(
    Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
)
```

`PassThrough` passes the raw fractional scale factor (e.g. 1.25, 1.5) directly to the
renderer instead of rounding to the nearest integer. This eliminates blurry text and
misaligned widget borders at 125 % and 150 % Windows display settings.
Qt 6 enables `AA_EnableHighDpiScaling` by default; no additional attribute flag is needed.

---

## 6. Validation Status

| Check | Result |
|---|---|
| Static analysis (`get_errors`) | No errors |
| Unit tests | 19 / 19 OK |
| Manual shortcut smoke-test | All shortcuts registered, no conflicts |

---

## Phase 4 Candidates

- **Export async migration** — `_export_active_report()` and `_export_comparison_report()` still block the UI thread; migrate to the same `QThread` worker pattern used in Phase 2
- **OpenStreetMap / Leaflet map** — replace `ScenarioMapCanvas` custom QPainter with `QWebEngineView` rendering Leaflet tiles with geo-aware overlays
- **WCAG contrast audit** — formal contrast ratio check of all `APP_STYLESHEET` colour pairs against WCAG 2.1 AA (4.5:1 for normal text)
