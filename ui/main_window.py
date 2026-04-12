from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from shutil import copyfile

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QAction, QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QCompleter,
    QDockWidget,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QInputDialog,
    QSpinBox,
    QSlider,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QScrollArea,
    QTreeWidget,
    QTreeWidgetItem,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from app.config import AppConfig
from domain.enums import HazardType, ScenarioStatus
from domain.models import (
    AnalysisSummary,
    AssumptionRecord,
    InventoryPosition,
    PersonnelRole,
    Scenario,
    TransportAsset,
)
from persistence.repositories import ScenarioRepository
from engine.planner import PlanningEngine
from domain.models import HazardProfile, InfrastructureProfile, PopulationProfile
from reference_data.geography import (
    format_location_label,
    geography_csv_path,
    geography_csv_schema_help_text,
    get_region_profile,
    get_world_region_for_country,
    list_countries_for_world_region,
    list_world_regions,
    list_regions,
    preview_geography_csv,
    parse_location_label,
    reload_region_profiles,
    validate_geography_csv,
)
from services.report_export import write_text_report
from services.report_templates import build_comparison_report, build_scenario_report, filtered_metric_deltas
from services.scenario_factory import build_default_scenario


def build_comparison_output_text(
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
) -> str:
    critical_delta = right_analysis.critical_coverage_percent - left_analysis.critical_coverage_percent
    overall_delta = right_analysis.overall_coverage_percent - left_analysis.overall_coverage_percent
    cost_delta = right_analysis.total_estimated_cost - left_analysis.total_estimated_cost

    lines = [
        f"Scenario A: {left_scenario.name} [{left_scenario.variant_label}]",
        f"Scenario B: {right_scenario.name} [{right_scenario.variant_label}]",
        f"Profile: {profile}",
        f"Profile weights: {profile_weights}",
        f"Metric filter: {metric_filter}",
        f"Lineage A: {lineage_left}",
        f"Lineage B: {lineage_right}",
        "",
        "Top-level deltas (B - A):",
        f"- Critical coverage: {critical_delta:+.1f}%",
        f"- Overall coverage: {overall_delta:+.1f}%",
        f"- Total estimated cost: ${cost_delta:+,.2f}",
        "",
        f"Comparison call: {winner}",
        "",
        "Detailed metric deltas:",
    ]

    deltas = filtered_metric_deltas(left_analysis.metadata, right_analysis.metadata, metric_filter)
    if deltas:
        for key, delta in deltas:
            lines.append(f"- {key}: {delta:+.2f}")
    else:
        lines.append("- No numeric metrics matched the selected filter.")

    lines.append("")
    lines.append("Scenario A unmet critical needs:")
    if left_analysis.unmet_critical_needs:
        lines.extend(f"- {item}" for item in left_analysis.unmet_critical_needs)
    else:
        lines.append("- None")

    lines.append("")
    lines.append("Scenario B unmet critical needs:")
    if right_analysis.unmet_critical_needs:
        lines.extend(f"- {item}" for item in right_analysis.unmet_critical_needs)
    else:
        lines.append("- None")

    return "\n".join(lines)


def build_timeline_projection_lines(scenario: Scenario, analysis: AnalysisSummary, day: int) -> list[str]:
    duration_days = max(1, scenario.hazard_profile.duration_days)
    clamped_day = max(1, min(day, duration_days))
    progress = clamped_day / duration_days

    critical_start = max(0.0, min(analysis.critical_coverage_percent * 0.55, 100.0))
    overall_start = max(0.0, min(analysis.overall_coverage_percent * 0.60, 100.0))
    critical_now = critical_start + (analysis.critical_coverage_percent - critical_start) * progress
    overall_now = overall_start + (analysis.overall_coverage_percent - overall_start) * progress

    displaced_population = scenario.population_profile.displaced_population
    unmet_start = max(len(analysis.unmet_critical_needs), int(displaced_population * 0.35))
    unmet_now = max(0, int(unmet_start * (1.0 - progress)))

    total_cost = analysis.total_estimated_cost
    projected_cost = total_cost * progress

    transport_days = analysis.metadata.get("transport_estimated_delivery_days")
    delivery_eta = None
    if isinstance(transport_days, (int, float)):
        delivery_eta = max(0.0, float(transport_days) - clamped_day)

    daily_capacity_kg = analysis.metadata.get("transport_daily_movable_capacity_kg")
    moved_tons = None
    if isinstance(daily_capacity_kg, (int, float)):
        moved_tons = (float(daily_capacity_kg) * clamped_day) / 1000.0

    lines = [
        f"Timeline Day {clamped_day}/{duration_days}",
        f"Hazard: {scenario.hazard_profile.hazard_type.value.title()} ({scenario.hazard_profile.severity_band})",
        f"Projected critical coverage: {critical_now:.1f}%",
        f"Projected overall coverage: {overall_now:.1f}%",
        f"Remaining unmet critical demand index: {unmet_now:,}",
        f"Cumulative operational spend: ${projected_cost:,.2f}",
    ]
    if delivery_eta is not None:
        lines.append(f"Estimated delivery ETA remaining: {delivery_eta:.1f} days")
    if moved_tons is not None:
        lines.append(f"Projected tonnage moved: {moved_tons:,.1f} tons")
    return lines


class ScenarioMapCanvas(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._latitude: float | None = None
        self._longitude: float | None = None
        self._location_label = ""
        self.setMinimumHeight(290)

    def set_location(self, latitude: float | None, longitude: float | None, label: str) -> None:
        self._latitude = latitude
        self._longitude = longitude
        self._location_label = label
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        canvas = self.rect().adjusted(10, 10, -10, -10)
        painter.fillRect(canvas, QColor("#dfe9f5"))
        painter.setPen(QPen(QColor("#9bb0c8"), 1))

        for step in range(1, 12):
            x = canvas.left() + int((canvas.width() * step) / 12)
            painter.drawLine(x, canvas.top(), x, canvas.bottom())
        for step in range(1, 6):
            y = canvas.top() + int((canvas.height() * step) / 6)
            painter.drawLine(canvas.left(), y, canvas.right(), y)

        painter.setPen(QPen(QColor("#6f859b"), 1.2))
        painter.drawRect(canvas)

        if self._latitude is None or self._longitude is None:
            painter.setPen(QColor("#39526d"))
            painter.drawText(canvas, Qt.AlignCenter, "Choose a location to place a scenario marker.")
            return

        marker_x = canvas.left() + ((self._longitude + 180.0) / 360.0) * canvas.width()
        marker_y = canvas.top() + ((90.0 - self._latitude) / 180.0) * canvas.height()
        marker_point = QRectF(marker_x - 7, marker_y - 7, 14, 14)

        painter.setPen(QPen(QColor("#8f1212"), 2))
        painter.setBrush(QColor("#d02d2d"))
        painter.drawEllipse(marker_point)

        painter.setPen(QPen(QColor("#9f1d1d"), 1, Qt.DashLine))
        painter.drawLine(int(marker_x), canvas.top(), int(marker_x), canvas.bottom())
        painter.drawLine(canvas.left(), int(marker_y), canvas.right(), int(marker_y))

        painter.setPen(QColor("#1f2c3a"))
        label = self._location_label or "Selected Location"
        painter.drawText(
            canvas.adjusted(12, 12, -12, -12),
            Qt.AlignTop | Qt.AlignLeft,
            f"{label}\nLat: {self._latitude:.4f}  Lon: {self._longitude:.4f}",
        )


class MainWindow(QMainWindow):
    def __init__(
        self,
        config: AppConfig,
        assumption_registry: tuple[AssumptionRecord, ...],
        scenario_repository: ScenarioRepository,
        planning_engine: PlanningEngine,
        active_scenario: Scenario,
        initial_analysis: AnalysisSummary,
    ) -> None:
        super().__init__()
        self.config = config
        self.assumption_registry = assumption_registry
        self.scenario_repository = scenario_repository
        self.planning_engine = planning_engine
        self.active_scenario = active_scenario
        self.initial_analysis = initial_analysis
        self.scenario_list_widget: QListWidget | None = None
        self.scenario_search_input: QLineEdit | None = None
        self.scenario_status_filter_combo: QComboBox | None = None
        self.summary_labels: dict[str, QLabel] = {}
        self.results_notes: QTextEdit | None = None

        self.name_input: QLineEdit | None = None
        self.world_region_combo: QComboBox | None = None
        self.country_combo: QComboBox | None = None
        self.region_combo: QComboBox | None = None
        self.latitude_input: QDoubleSpinBox | None = None
        self.longitude_input: QDoubleSpinBox | None = None
        self.notes_input: QTextEdit | None = None
        self.validation_banner: QLabel | None = None
        self.change_preview: QTextEdit | None = None
        self.hazard_combo: QComboBox | None = None
        self.severity_input: QLineEdit | None = None
        self.duration_input: QSpinBox | None = None
        self.infrastructure_damage_input: QDoubleSpinBox | None = None
        self.total_population_input: QSpinBox | None = None
        self.displaced_population_input: QSpinBox | None = None
        self.children_input: QSpinBox | None = None
        self.older_adults_input: QSpinBox | None = None
        self.pregnant_input: QSpinBox | None = None
        self.medically_vulnerable_input: QSpinBox | None = None
        self.road_access_input: QDoubleSpinBox | None = None
        self.health_operability_input: QDoubleSpinBox | None = None
        self.water_availability_input: QDoubleSpinBox | None = None
        self.food_supply_ratio_input: QDoubleSpinBox | None = None
        self.resource_table: QTableWidget | None = None
        self.personnel_table: QTableWidget | None = None
        self.transport_table: QTableWidget | None = None
        self.workspace_tabs: QTabWidget | None = None
        self.compare_left_combo: QComboBox | None = None
        self.compare_right_combo: QComboBox | None = None
        self.comparison_profile_combo: QComboBox | None = None
        self.metric_filter_combo: QComboBox | None = None
        self.compare_output: QTextEdit | None = None
        self.lineage_tree: QTreeWidget | None = None
        self.compare_tab_index: int | None = None
        self.map_tab_index: int | None = None
        self.map_canvas: ScenarioMapCanvas | None = None
        self.timeline_slider: QSlider | None = None
        self.timeline_day_label: QLabel | None = None
        self.timeline_summary: QTextEdit | None = None
        self.editor_inputs: list[QWidget] = []
        self.compare_kpi_labels: dict[str, QLabel] = {}
        self.resource_add_button: QPushButton | None = None
        self.resource_remove_button: QPushButton | None = None
        self.personnel_add_button: QPushButton | None = None
        self.personnel_remove_button: QPushButton | None = None
        self.transport_add_button: QPushButton | None = None
        self.transport_remove_button: QPushButton | None = None
        self.save_button: QPushButton | None = None
        self.last_comparison_payload: dict[str, object] | None = None
        self._suppress_geo_autofill = False

        self.setWindowTitle("DRASTIC Planner")
        self.resize(1480, 920)
        self._apply_modern_theme()

        self._build_toolbar()
        self._build_left_navigation()
        self._build_summary_dock()
        self._build_central_workspace()
        self.setStatusBar(QStatusBar(self))
        self.statusBar().showMessage(f"Offline-first mode enabled • Database: {self.config.database_path}")

    def _apply_modern_theme(self) -> None:
        self.setFont(QFont("Segoe UI Variable", 11))
        self.setStyleSheet(
            """
            QMainWindow {
                background-color: #f2f5f8;
            }
            QDockWidget::title {
                background: #e8eef3;
                color: #163447;
                padding: 8px 10px;
                font-weight: 600;
                border-bottom: 1px solid #d3dde6;
            }
            QToolBar {
                background: #f8fafc;
                border: 1px solid #dbe5ed;
                spacing: 8px;
                padding: 6px;
            }
            QToolButton {
                background: #1474a3;
                color: #ffffff;
                border: 1px solid #0f628a;
                border-radius: 6px;
                padding: 7px 12px;
                font-weight: 600;
            }
            QToolButton:hover {
                background: #0f678f;
            }
            QTabWidget::pane {
                border: 1px solid #d4dfe8;
                background: #ffffff;
            }
            QTabBar::tab {
                background: #edf2f7;
                color: #22323d;
                border: 1px solid #d4dfe8;
                border-bottom: none;
                padding: 8px 12px;
                margin-right: 4px;
                min-width: 110px;
            }
            QTabBar::tab:selected {
                background: #ffffff;
                color: #0e4f70;
                font-weight: 700;
            }
            QLabel {
                color: #1b2d3a;
                font-size: 12px;
            }
            QLabel#SectionHeader {
                font-size: 14px;
                font-weight: 700;
                color: #0f5679;
                margin-top: 10px;
                margin-bottom: 4px;
            }
            QLabel#SubtleHint {
                color: #4f6573;
                margin-bottom: 6px;
            }
            QLabel#ValidationBanner {
                background: #fff0f0;
                color: #8a1b1b;
                border: 1px solid #efc1c1;
                border-radius: 6px;
                padding: 8px;
                font-weight: 600;
            }
            QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit {
                border: 1px solid #c2d0da;
                border-radius: 6px;
                background: #ffffff;
                color: #142836;
                padding: 6px;
                selection-background-color: #1f84b3;
            }
            QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
                min-height: 34px;
            }
            QComboBox QAbstractItemView {
                background: #ffffff;
                color: #142836;
                border: 1px solid #c2d0da;
                selection-background-color: #d9edf9;
                selection-color: #0f3550;
                outline: 0;
            }
            QComboBox::drop-down {
                border: none;
                width: 26px;
            }
            QTextEdit {
                min-height: 120px;
            }
            QPushButton {
                background: #ffffff;
                color: #145d80;
                border: 1px solid #aac0cf;
                border-radius: 6px;
                padding: 7px 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #e8f2f8;
            }
            QTableWidget, QTreeWidget, QListWidget {
                background: #ffffff;
                border: 1px solid #d4dfe8;
                color: #142631;
                gridline-color: #e7edf2;
                alternate-background-color: #f4f9fc;
            }
            QHeaderView::section {
                background: #edf4f9;
                color: #1f2e38;
                border: 1px solid #d2dbe2;
                padding: 6px;
                font-weight: 700;
            }
            QScrollArea {
                border: none;
                background: #ffffff;
            }
            QScrollArea > QWidget > QWidget#ScenarioContent {
                background: #ffffff;
            }
            QLabel#MetricLabel {
                background: #eef5fb;
                border: 1px solid #c7d8e5;
                border-radius: 6px;
                color: #12384d;
                font-size: 12px;
                font-weight: 700;
                padding: 6px;
            }
            QLabel#CompareCard {
                background: #f4f9fd;
                border: 1px solid #c8d9e6;
                border-radius: 8px;
                color: #12384d;
                font-size: 12px;
                font-weight: 700;
                padding: 8px;
                min-height: 44px;
            }
            QStatusBar {
                background: #f5f8fb;
                color: #1a3c51;
            }
            """
        )

    def _section_header(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("SectionHeader")
        return label

    def _subtle_hint(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("SubtleHint")
        label.setWordWrap(True)
        return label

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("Main Toolbar", self)
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        new_project_action = QAction("New Scenario", self)
        new_project_action.setStatusTip("Create a new scenario planning record")
        new_project_action.triggered.connect(self._create_new_scenario)
        toolbar.addAction(new_project_action)

        save_action = QAction("Save Scenario", self)
        save_action.setStatusTip("Persist the active scenario to SQLite")
        save_action.triggered.connect(self._save_active_scenario)
        toolbar.addAction(save_action)

        analyze_action = QAction("Run Analysis", self)
        analyze_action.setStatusTip("Analyze the active scenario with the planning engine")
        analyze_action.triggered.connect(self._run_analysis)
        toolbar.addAction(analyze_action)

        branch_action = QAction("Branch Variant", self)
        branch_action.setStatusTip("Create a variant from the active scenario")
        branch_action.triggered.connect(self._branch_variant)
        toolbar.addAction(branch_action)

        lock_action = QAction("Lock Baseline", self)
        lock_action.setStatusTip("Lock baseline scenario from direct edits")
        lock_action.triggered.connect(self._lock_baseline)
        toolbar.addAction(lock_action)

        compare_action = QAction("Compare Variants", self)
        compare_action.setStatusTip("Open the scenario comparison workspace")
        compare_action.triggered.connect(self._open_compare_tab)
        toolbar.addAction(compare_action)

        export_action = QAction("Export", self)
        export_action.setStatusTip("Export the active scenario package")
        export_action.triggered.connect(self._export_active_report)
        toolbar.addAction(export_action)

        reload_geo_action = QAction("Reload Geography", self)
        reload_geo_action.setStatusTip("Validate and reload location catalog from CSV")
        reload_geo_action.triggered.connect(self._reload_geography_catalog)
        toolbar.addAction(reload_geo_action)

        import_geo_action = QAction("Import Geography CSV", self)
        import_geo_action.setStatusTip("Import an external geography CSV and reload location catalog")
        import_geo_action.triggered.connect(self._import_geography_catalog)
        toolbar.addAction(import_geo_action)

        geo_schema_action = QAction("Geography CSV Help", self)
        geo_schema_action.setStatusTip("Show required columns and sample row for geography CSV")
        geo_schema_action.triggered.connect(self._show_geography_csv_help)
        toolbar.addAction(geo_schema_action)

    def _show_geography_csv_help(self) -> None:
        QMessageBox.information(
            self,
            "Geography CSV Help",
            geography_csv_schema_help_text(),
        )

    def _import_geography_catalog(self) -> None:
        selected_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Geography CSV",
            str(geography_csv_path().parent),
            "CSV Files (*.csv)",
        )
        if not selected_path:
            return

        source_path = Path(selected_path)
        if not source_path.exists() or not source_path.is_file():
            QMessageBox.warning(self, "Import Geography", "Selected file does not exist.")
            return

        errors = validate_geography_csv(source_path)
        if errors:
            preview = "\n".join(errors[:12])
            QMessageBox.warning(
                self,
                "Geography CSV Validation",
                f"Cannot import this file due to validation issues:\n{preview}",
            )
            return

        preview_data = preview_geography_csv(source_path)
        preview_lines = [
            f"File: {source_path.name}",
            f"Rows: {preview_data['total_rows']}",
            f"World regions: {len(preview_data['world_regions'])}",
            f"Countries: {len(preview_data['countries'])}",
            "",
            "Sample rows:",
        ]
        preview_lines.extend(preview_data["sample_rows"])

        confirm = QMessageBox.question(
            self,
            "Confirm Geography Import",
            "\n".join(preview_lines),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return

        target_path = geography_csv_path()
        if source_path.resolve() != target_path.resolve():
            copyfile(source_path, target_path)

        loaded_count = self._reload_geography_catalog()
        if loaded_count is not None:
            self.statusBar().showMessage(
                f"Imported and reloaded geography catalog ({loaded_count} region profiles)"
            )

    def _reload_geography_catalog(self) -> int | None:
        errors = validate_geography_csv()
        if errors:
            preview = "\n".join(errors[:8])
            QMessageBox.warning(
                self,
                "Geography CSV Validation",
                f"Geography catalog has validation issues:\n{preview}",
            )
            return None

        old_world_region = self._selected_world_region()
        old_country = self._selected_country()
        old_region = self._selected_region()

        loaded_count = reload_region_profiles()

        if self.world_region_combo is not None:
            self.world_region_combo.blockSignals(True)
            self.world_region_combo.clear()
            self.world_region_combo.addItems(list_world_regions())
            self.world_region_combo.blockSignals(False)

        if old_world_region and self.world_region_combo is not None:
            world_index = self.world_region_combo.findText(old_world_region)
            if world_index >= 0:
                self.world_region_combo.setCurrentIndex(world_index)

        selected_world_region = self._selected_world_region()
        if selected_world_region:
            self._sync_countries_for_world_region(selected_world_region)

        if old_country and self.country_combo is not None:
            country_index = self.country_combo.findText(old_country)
            if country_index >= 0:
                self.country_combo.setCurrentIndex(country_index)
                self._sync_regions_for_country(old_country)

        if old_region and self.region_combo is not None:
            region_index = self.region_combo.findText(old_region)
            if region_index >= 0:
                self.region_combo.setCurrentIndex(region_index)

        self._on_region_changed()
        self.statusBar().showMessage(
            f"Reloaded geography catalog ({loaded_count} region profiles) from {geography_csv_path().name}"
        )
        return loaded_count

    def _build_left_navigation(self) -> None:
        navigation_dock = QDockWidget("Scenarios", self)
        navigation_dock.setAllowedAreas(Qt.LeftDockWidgetArea)

        wrapper = QWidget()
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(8, 8, 8, 8)
        wrapper_layout.setSpacing(6)

        self.scenario_search_input = QLineEdit()
        self.scenario_search_input.setPlaceholderText("Search scenarios...")
        self.scenario_search_input.textChanged.connect(lambda _value: self._refresh_scenario_list())

        self.scenario_status_filter_combo = QComboBox()
        self.scenario_status_filter_combo.addItems(["All Statuses", "Draft", "Review", "Locked"])
        self.scenario_status_filter_combo.currentIndexChanged.connect(lambda _idx: self._refresh_scenario_list())

        scenario_list = QListWidget()
        scenario_list.setAlternatingRowColors(True)
        scenario_list.itemSelectionChanged.connect(self._load_selected_scenario)
        self.scenario_list_widget = scenario_list

        wrapper_layout.addWidget(self.scenario_search_input)
        wrapper_layout.addWidget(self.scenario_status_filter_combo)
        wrapper_layout.addWidget(scenario_list)

        navigation_dock.setWidget(wrapper)
        self.addDockWidget(Qt.LeftDockWidgetArea, navigation_dock)
        navigation_dock.setMinimumWidth(290)
        self._refresh_scenario_list()

    def _build_summary_dock(self) -> None:
        summary_dock = QDockWidget("Live Summary", self)
        summary_dock.setAllowedAreas(Qt.RightDockWidgetArea)

        summary_widget = QWidget()
        layout = QVBoxLayout(summary_widget)
        layout.addWidget(QLabel("Critical Coverage"))
        self.summary_labels["critical"] = QLabel()
        self.summary_labels["critical"].setObjectName("MetricLabel")
        layout.addWidget(self.summary_labels["critical"])
        layout.addWidget(QLabel("Overall Coverage"))
        self.summary_labels["overall"] = QLabel()
        self.summary_labels["overall"].setObjectName("MetricLabel")
        layout.addWidget(self.summary_labels["overall"])
        layout.addWidget(QLabel("Estimated Cost"))
        self.summary_labels["cost"] = QLabel()
        self.summary_labels["cost"].setObjectName("MetricLabel")
        layout.addWidget(self.summary_labels["cost"])
        layout.addWidget(QLabel("Confidence"))
        self.summary_labels["confidence"] = QLabel()
        self.summary_labels["confidence"].setObjectName("MetricLabel")
        layout.addWidget(self.summary_labels["confidence"])
        layout.addWidget(QLabel("Risk Flags"))
        self.summary_labels["risks"] = QLabel()
        self.summary_labels["risks"].setWordWrap(True)
        layout.addWidget(self.summary_labels["risks"])
        layout.addStretch(1)

        summary_dock.setWidget(summary_widget)
        self.addDockWidget(Qt.RightDockWidgetArea, summary_dock)
        self._update_summary_panel(self.initial_analysis)

    def _build_central_workspace(self) -> None:
        tabs = QTabWidget(self)
        tabs.addTab(self._build_overview_tab(), "Scenario")
        tabs.addTab(self._build_assumptions_tab(), "Assumptions")
        tabs.addTab(self._build_results_tab(), "Results")
        self.map_tab_index = tabs.addTab(self._build_map_tab(), "Map Simulation")
        self.compare_tab_index = tabs.addTab(self._build_compare_tab(), "Compare")
        self.workspace_tabs = tabs
        self.setCentralWidget(tabs)

    def _build_overview_tab(self) -> QWidget:
        content = QWidget()
        content.setObjectName("ScenarioContent")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)

        context_form = QFormLayout()
        population_form = QFormLayout()
        infrastructure_form = QFormLayout()
        for form in (context_form, population_form, infrastructure_form):
            form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            form.setFormAlignment(Qt.AlignTop)
            form.setHorizontalSpacing(16)
            form.setVerticalSpacing(8)
        self.name_input = QLineEdit()
        self.world_region_combo = QComboBox()
        self.country_combo = QComboBox()
        self.region_combo = QComboBox()
        self._enable_combo_search(self.world_region_combo)
        self._enable_combo_search(self.country_combo)
        self._enable_combo_search(self.region_combo)
        self.world_region_combo.addItems(list_world_regions())
        self.world_region_combo.currentIndexChanged.connect(self._on_world_region_changed)
        self.country_combo.currentIndexChanged.connect(self._on_country_changed)
        self.region_combo.currentIndexChanged.connect(self._on_region_changed)

        self.latitude_input = QDoubleSpinBox()
        self.latitude_input.setRange(-90.0, 90.0)
        self.latitude_input.setDecimals(4)
        self.latitude_input.valueChanged.connect(lambda _value: self._refresh_map_location_preview())
        self.longitude_input = QDoubleSpinBox()
        self.longitude_input.setRange(-180.0, 180.0)
        self.longitude_input.setDecimals(4)
        self.longitude_input.valueChanged.connect(lambda _value: self._refresh_map_location_preview())
        self.hazard_combo = QComboBox()
        for hazard in HazardType:
            self.hazard_combo.addItem(hazard.value, hazard)
        self.severity_input = QLineEdit()
        self.duration_input = QSpinBox()
        self.duration_input.setRange(1, 365)
        self.infrastructure_damage_input = QDoubleSpinBox()
        self.infrastructure_damage_input.setRange(0.0, 100.0)
        self.infrastructure_damage_input.setDecimals(1)

        self.total_population_input = QSpinBox()
        self.total_population_input.setRange(0, 100000000)
        self.displaced_population_input = QSpinBox()
        self.displaced_population_input.setRange(0, 100000000)
        self.children_input = QSpinBox()
        self.children_input.setRange(0, 100000000)
        self.older_adults_input = QSpinBox()
        self.older_adults_input.setRange(0, 100000000)
        self.pregnant_input = QSpinBox()
        self.pregnant_input.setRange(0, 100000000)
        self.medically_vulnerable_input = QSpinBox()
        self.medically_vulnerable_input.setRange(0, 100000000)

        self.road_access_input = QDoubleSpinBox()
        self.road_access_input.setRange(0.0, 1.0)
        self.road_access_input.setDecimals(2)
        self.health_operability_input = QDoubleSpinBox()
        self.health_operability_input.setRange(0.0, 1.0)
        self.health_operability_input.setDecimals(2)
        self.water_availability_input = QDoubleSpinBox()
        self.water_availability_input.setRange(0.0, 1000000000.0)
        self.water_availability_input.setDecimals(1)
        self.food_supply_ratio_input = QDoubleSpinBox()
        self.food_supply_ratio_input.setRange(0.0, 1.0)
        self.food_supply_ratio_input.setDecimals(2)

        self.notes_input = QTextEdit()
        self.notes_input.setMinimumHeight(110)

        self.editor_inputs.extend(
            [
                self.name_input,
                self.world_region_combo,
                self.country_combo,
                self.region_combo,
                self.latitude_input,
                self.longitude_input,
                self.hazard_combo,
                self.severity_input,
                self.duration_input,
                self.infrastructure_damage_input,
                self.total_population_input,
                self.displaced_population_input,
                self.children_input,
                self.older_adults_input,
                self.pregnant_input,
                self.medically_vulnerable_input,
                self.road_access_input,
                self.health_operability_input,
                self.water_availability_input,
                self.food_supply_ratio_input,
                self.notes_input,
            ]
        )

        context_form.addRow("Scenario Name", self.name_input)
        context_form.addRow("World Region", self.world_region_combo)
        context_form.addRow("Country", self.country_combo)
        context_form.addRow("Region/State", self.region_combo)
        context_form.addRow("Latitude", self.latitude_input)
        context_form.addRow("Longitude", self.longitude_input)
        context_form.addRow("Hazard", self.hazard_combo)
        context_form.addRow("Severity Band", self.severity_input)
        context_form.addRow("Duration (days)", self.duration_input)
        context_form.addRow("Notes", self.notes_input)

        population_form.addRow("Total Population", self.total_population_input)
        population_form.addRow("Displaced Population", self.displaced_population_input)
        population_form.addRow("Children Under 5", self.children_input)
        population_form.addRow("Older Adults", self.older_adults_input)
        population_form.addRow("Pregnant/Lactating", self.pregnant_input)
        population_form.addRow("Medically Vulnerable", self.medically_vulnerable_input)

        infrastructure_form.addRow("Infrastructure Damage %", self.infrastructure_damage_input)
        infrastructure_form.addRow("Road Access Score", self.road_access_input)
        infrastructure_form.addRow("Health Facility Operability", self.health_operability_input)
        infrastructure_form.addRow("Local Water Liters/Day", self.water_availability_input)
        infrastructure_form.addRow("Local Food Supply Ratio", self.food_supply_ratio_input)

        self.resource_table = QTableWidget(0, 5, content)
        self.resource_table.setHorizontalHeaderLabels(
            ["Name", "Category", "Quantity", "Unit", "Priority"]
        )
        self.resource_table.setAlternatingRowColors(True)
        self.resource_table.setMinimumHeight(140)
        self.resource_table.horizontalHeader().setStretchLastSection(True)
        resource_controls, self.resource_add_button, self.resource_remove_button = self._build_table_controls(
            on_add=self._add_resource_row,
            on_remove=lambda: self._remove_selected_rows(self.resource_table),
        )

        self.personnel_table = QTableWidget(0, 5, content)
        self.personnel_table.setHorizontalHeaderLabels(
            ["Role", "Count", "Shift Hours", "Hourly Cost", "Volunteers"]
        )
        self.personnel_table.setAlternatingRowColors(True)
        self.personnel_table.setMinimumHeight(140)
        self.personnel_table.horizontalHeader().setStretchLastSection(True)
        personnel_controls, self.personnel_add_button, self.personnel_remove_button = self._build_table_controls(
            on_add=self._add_personnel_row,
            on_remove=lambda: self._remove_selected_rows(self.personnel_table),
        )

        self.transport_table = QTableWidget(0, 6, content)
        self.transport_table.setHorizontalHeaderLabels(
            ["Asset", "Capacity (kg)", "Quantity", "Speed (km/h)", "Reliability", "Cost/km"]
        )
        self.transport_table.setAlternatingRowColors(True)
        self.transport_table.setMinimumHeight(140)
        self.transport_table.horizontalHeader().setStretchLastSection(True)
        transport_controls, self.transport_add_button, self.transport_remove_button = self._build_table_controls(
            on_add=self._add_transport_row,
            on_remove=lambda: self._remove_selected_rows(self.transport_table),
        )

        button_row = QWidget()
        button_layout = QVBoxLayout(button_row)
        save_button = QPushButton("Save Scenario")
        save_button.clicked.connect(self._save_active_scenario)
        self.save_button = save_button
        analyze_button = QPushButton("Analyze Scenario")
        analyze_button.clicked.connect(self._run_analysis)
        preview_button = QPushButton("Preview Changes")
        preview_button.clicked.connect(self._preview_changes)
        button_layout.addWidget(save_button)
        button_layout.addWidget(analyze_button)
        button_layout.addWidget(preview_button)

        self.validation_banner = QLabel("")
        self.validation_banner.setObjectName("ValidationBanner")
        self.validation_banner.setWordWrap(True)
        self.validation_banner.hide()

        self.change_preview = QTextEdit()
        self.change_preview.setReadOnly(True)
        self.change_preview.setMinimumHeight(140)
        self.change_preview.setPlainText("Run Preview Changes to review edits before save/analyze.")

        layout.addWidget(self._section_header("Scenario Context"))
        layout.addWidget(self._subtle_hint("Set location and baseline conditions before analysis."))
        layout.addLayout(context_form)
        layout.addWidget(self._section_header("Population Profile"))
        layout.addLayout(population_form)
        layout.addWidget(self._section_header("Infrastructure Profile"))
        layout.addLayout(infrastructure_form)
        layout.addWidget(self.validation_banner)
        layout.addWidget(self._section_header("Resources"))
        layout.addWidget(self.resource_table)
        layout.addLayout(resource_controls)
        layout.addWidget(self._section_header("Personnel"))
        layout.addWidget(self.personnel_table)
        layout.addLayout(personnel_controls)
        layout.addWidget(self._section_header("Transportation"))
        layout.addWidget(self.transport_table)
        layout.addLayout(transport_controls)
        layout.addWidget(button_row)
        layout.addWidget(self._section_header("Change Preview"))
        layout.addWidget(self.change_preview)
        layout.addStretch(1)
        if self.world_region_combo.count() > 0:
            self._sync_countries_for_world_region(self.world_region_combo.itemText(0))
        self._populate_editor_from_scenario(self.active_scenario)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(content)
        return scroll

    def _build_table_controls(self, on_add: callable, on_remove: callable) -> tuple[QHBoxLayout, QPushButton, QPushButton]:
        controls = QHBoxLayout()
        add_button = QPushButton("Add Row")
        add_button.clicked.connect(on_add)
        remove_button = QPushButton("Remove Selected")
        remove_button.clicked.connect(on_remove)
        controls.addWidget(add_button)
        controls.addWidget(remove_button)
        controls.addStretch(1)
        return controls, add_button, remove_button

    def _add_resource_row(self) -> None:
        if self.resource_table is None:
            return
        self._insert_row(
            self.resource_table,
            ["Resource", "water", "0", "liters", "1"],
        )

    def _add_personnel_row(self) -> None:
        if self.personnel_table is None:
            return
        self._insert_row(
            self.personnel_table,
            ["Role", "0", "8", "0", "0"],
        )

    def _add_transport_row(self) -> None:
        if self.transport_table is None:
            return
        self._insert_row(
            self.transport_table,
            ["Asset", "0", "1", "40", "0.8", "0"],
        )

    def _insert_row(self, table: QTableWidget, values: list[str]) -> None:
        row = table.rowCount()
        table.insertRow(row)
        for col, value in enumerate(values):
            table.setItem(row, col, QTableWidgetItem(value))

    def _remove_selected_rows(self, table: QTableWidget | None) -> None:
        if table is None:
            return
        selected_rows = {index.row() for index in table.selectedIndexes()}
        for row in sorted(selected_rows, reverse=True):
            table.removeRow(row)

    def _build_assumptions_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        table = QTableWidget(len(self.assumption_registry), 6, widget)
        table.setHorizontalHeaderLabels(
            ["Identifier", "Category", "Baseline", "Unit", "Source", "Confidence"]
        )
        table.horizontalHeader().setStretchLastSection(True)

        for row, assumption in enumerate(self.assumption_registry):
            table.setItem(row, 0, QTableWidgetItem(assumption.identifier))
            table.setItem(row, 1, QTableWidgetItem(assumption.category.value))
            table.setItem(row, 2, QTableWidgetItem(str(assumption.baseline_value)))
            table.setItem(row, 3, QTableWidgetItem(assumption.unit))
            table.setItem(row, 4, QTableWidgetItem(assumption.source_name))
            table.setItem(row, 5, QTableWidgetItem(assumption.confidence_level.value))

        layout.addWidget(self._section_header("Assumption Registry"))
        layout.addWidget(self._subtle_hint("Assumptions are traceable references used by the planning engine."))
        layout.addWidget(table)
        return widget

    def _build_results_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        notes = QTextEdit()
        notes.setReadOnly(True)
        notes.setFont(QFont("Consolas", 10))
        self.results_notes = notes
        self._update_results_view(self.initial_analysis)
        layout.addWidget(self._section_header("Planning Results"))
        layout.addWidget(self._subtle_hint("Review computed metrics, unmet needs, and assumptions trace."))
        layout.addWidget(notes)
        return widget

    def _build_map_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        self.map_canvas = ScenarioMapCanvas(widget)
        layout.addWidget(self._section_header("Operational Map"))
        layout.addWidget(self._subtle_hint("Marker updates from selected coordinates and timeline day."))
        layout.addWidget(self.map_canvas)

        timeline_row = QHBoxLayout()
        timeline_row.addWidget(QLabel("Timeline"))
        self.timeline_slider = QSlider(Qt.Horizontal)
        self.timeline_slider.setRange(1, max(1, self.active_scenario.hazard_profile.duration_days))
        self.timeline_slider.setValue(1)
        self.timeline_slider.setTickPosition(QSlider.TicksBelow)
        self.timeline_slider.setSingleStep(1)
        self.timeline_slider.valueChanged.connect(self._on_timeline_day_changed)
        self.timeline_day_label = QLabel("Day 1")
        timeline_row.addWidget(self.timeline_slider)
        timeline_row.addWidget(self.timeline_day_label)
        layout.addLayout(timeline_row)

        self.timeline_summary = QTextEdit()
        self.timeline_summary.setReadOnly(True)
        self.timeline_summary.setFont(QFont("Consolas", 10))
        self.timeline_summary.setMinimumHeight(180)
        layout.addWidget(self._section_header("Simulation Snapshot"))
        layout.addWidget(self.timeline_summary)

        self._refresh_map_tab(self.active_scenario, self.initial_analysis)
        return widget

    def _build_compare_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        selector_row = QHBoxLayout()
        self.compare_left_combo = QComboBox()
        self.compare_right_combo = QComboBox()
        self.comparison_profile_combo = QComboBox()
        self.comparison_profile_combo.addItems(["Balanced", "Coverage First", "Cost First"])
        self.metric_filter_combo = QComboBox()
        self.metric_filter_combo.addItems(["All Metrics", "Coverage", "Cost", "Staffing", "Transport"])
        self.compare_left_combo.currentIndexChanged.connect(self._run_comparison)
        self.compare_right_combo.currentIndexChanged.connect(self._run_comparison)
        self.comparison_profile_combo.currentIndexChanged.connect(self._run_comparison)
        self.metric_filter_combo.currentIndexChanged.connect(self._run_comparison)
        run_compare_button = QPushButton("Run Comparison")
        run_compare_button.clicked.connect(self._run_comparison)
        copy_compare_button = QPushButton("Copy Summary")
        copy_compare_button.clicked.connect(self._copy_comparison_output)
        swap_button = QPushButton("Swap")
        swap_button.clicked.connect(self._swap_comparison_selection)
        export_compare_button = QPushButton("Export Comparison")
        export_compare_button.clicked.connect(self._export_comparison_report)

        branch_selected_button = QPushButton("Branch Selected")
        branch_selected_button.clicked.connect(self._branch_selected_tree_node)
        compare_selected_button = QPushButton("Compare Selected vs Active")
        compare_selected_button.clicked.connect(self._compare_selected_with_active)
        lock_selected_button = QPushButton("Lock Selected Baseline")
        lock_selected_button.clicked.connect(self._lock_selected_tree_node)
        unlock_selected_button = QPushButton("Unlock Selected Baseline")
        unlock_selected_button.clicked.connect(self._unlock_selected_tree_node)

        selector_row.addWidget(QLabel("Scenario A"))
        selector_row.addWidget(self.compare_left_combo)
        selector_row.addWidget(QLabel("Scenario B"))
        selector_row.addWidget(self.compare_right_combo)
        selector_row.addWidget(QLabel("Profile"))
        selector_row.addWidget(self.comparison_profile_combo)
        selector_row.addWidget(QLabel("Metrics"))
        selector_row.addWidget(self.metric_filter_combo)
        selector_row.addWidget(swap_button)
        selector_row.addWidget(run_compare_button)
        selector_row.addWidget(copy_compare_button)
        selector_row.addWidget(export_compare_button)

        kpi_row = QGridLayout()
        kpi_row.setHorizontalSpacing(10)
        kpi_row.setVerticalSpacing(8)
        self.compare_kpi_labels["critical_delta"] = QLabel("Critical delta: n/a")
        self.compare_kpi_labels["overall_delta"] = QLabel("Overall delta: n/a")
        self.compare_kpi_labels["cost_delta"] = QLabel("Cost delta: n/a")
        self.compare_kpi_labels["delivery_days_delta"] = QLabel("Delivery days delta: n/a")
        self.compare_kpi_labels["daily_capacity_delta"] = QLabel("Daily capacity delta: n/a")
        self.compare_kpi_labels["winner"] = QLabel("Winner: n/a")
        for label in self.compare_kpi_labels.values():
            label.setObjectName("CompareCard")
            label.setWordWrap(True)
        kpi_row.addWidget(self.compare_kpi_labels["critical_delta"], 0, 0)
        kpi_row.addWidget(self.compare_kpi_labels["overall_delta"], 0, 1)
        kpi_row.addWidget(self.compare_kpi_labels["cost_delta"], 0, 2)
        kpi_row.addWidget(self.compare_kpi_labels["delivery_days_delta"], 1, 0)
        kpi_row.addWidget(self.compare_kpi_labels["daily_capacity_delta"], 1, 1)
        kpi_row.addWidget(self.compare_kpi_labels["winner"], 1, 2)

        tree_actions = QHBoxLayout()
        tree_actions.addWidget(branch_selected_button)
        tree_actions.addWidget(compare_selected_button)
        tree_actions.addWidget(lock_selected_button)
        tree_actions.addWidget(unlock_selected_button)
        tree_actions.addStretch(1)

        lineage_tree = QTreeWidget()
        lineage_tree.setHeaderLabels(["Scenario Branch Tree"])
        lineage_tree.setMinimumHeight(220)
        self.lineage_tree = lineage_tree

        output = QTextEdit()
        output.setReadOnly(True)
        output.setFont(QFont("Consolas", 10))
        output.setMinimumHeight(260)
        output.setPlainText("Select two scenarios and run comparison to view analysis deltas.")
        self.compare_output = output

        layout.addWidget(self._section_header("Comparison Workspace"))
        layout.addWidget(self._subtle_hint("Compare two scenarios using profile and metric filters."))
        layout.addLayout(selector_row)
        layout.addLayout(kpi_row)
        layout.addWidget(self._section_header("Branch Lineage"))
        layout.addWidget(lineage_tree)
        layout.addLayout(tree_actions)
        layout.addWidget(output)
        self._refresh_lineage_tree()
        return widget

    def _refresh_scenario_list(self, selected_scenario_id: str | None = None) -> None:
        if self.scenario_list_widget is None:
            return

        self.scenario_list_widget.blockSignals(True)
        self.scenario_list_widget.clear()
        summaries = self.scenario_repository.list_scenarios()
        search_text = self.scenario_search_input.text().strip().lower() if self.scenario_search_input else ""
        selected_status = self.scenario_status_filter_combo.currentText() if self.scenario_status_filter_combo else "All Statuses"
        for summary in summaries:
            if selected_status != "All Statuses" and summary.status.value != selected_status.lower():
                continue
            searchable = f"{summary.name} {summary.variant_label} {summary.hazard_type.value} {summary.location_label}".lower()
            if search_text and search_text not in searchable:
                continue
            variant_text = f"[{summary.variant_label}]"
            status_text = f"({summary.status.value})"
            label = f"{summary.name} {variant_text} {status_text} • {summary.hazard_type.value} • {summary.location_label}"
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, summary.scenario_id)
            self.scenario_list_widget.addItem(item)
            if selected_scenario_id and summary.scenario_id == selected_scenario_id:
                item.setSelected(True)

        if not selected_scenario_id and summaries:
            self.scenario_list_widget.setCurrentRow(0)
        self.scenario_list_widget.blockSignals(False)
        self._refresh_compare_selectors(summaries)
        self._refresh_lineage_tree()

    def _refresh_lineage_tree(self) -> None:
        if self.lineage_tree is None:
            return

        summaries = self.scenario_repository.list_scenarios()
        by_id = {summary.scenario_id: summary for summary in summaries}
        children_by_parent: dict[str, list] = {}
        roots = []

        for summary in summaries:
            parent_id = summary.base_scenario_id
            if parent_id and parent_id in by_id:
                children_by_parent.setdefault(parent_id, []).append(summary)
            else:
                roots.append(summary)

        self.lineage_tree.clear()

        def add_node(parent_item: QTreeWidgetItem | None, summary) -> None:
            label = f"{summary.name} [{summary.variant_label}] ({summary.status.value})"
            node = QTreeWidgetItem([label])
            node.setData(0, Qt.UserRole, summary.scenario_id)
            if parent_item is None:
                self.lineage_tree.addTopLevelItem(node)
            else:
                parent_item.addChild(node)
            children = children_by_parent.get(summary.scenario_id, [])
            children.sort(key=lambda s: s.updated_at)
            for child in children:
                add_node(node, child)

        roots.sort(key=lambda s: s.updated_at)
        for root in roots:
            add_node(None, root)
        self.lineage_tree.expandAll()

    def _refresh_compare_selectors(self, summaries: list) -> None:
        if self.compare_left_combo is None or self.compare_right_combo is None:
            return

        current_left = self.compare_left_combo.currentData()
        current_right = self.compare_right_combo.currentData()

        self.compare_left_combo.blockSignals(True)
        self.compare_right_combo.blockSignals(True)
        self.compare_left_combo.clear()
        self.compare_right_combo.clear()

        for summary in summaries:
            label = f"{summary.name} [{summary.variant_label}]"
            self.compare_left_combo.addItem(label, summary.scenario_id)
            self.compare_right_combo.addItem(label, summary.scenario_id)

        if summaries:
            left_index = self.compare_left_combo.findData(current_left)
            right_index = self.compare_right_combo.findData(current_right)
            self.compare_left_combo.setCurrentIndex(left_index if left_index >= 0 else 0)
            default_right = 1 if len(summaries) > 1 else 0
            self.compare_right_combo.setCurrentIndex(right_index if right_index >= 0 else default_right)

        self.compare_left_combo.blockSignals(False)
        self.compare_right_combo.blockSignals(False)

    def _populate_editor_from_scenario(self, scenario: Scenario) -> None:
        if not self.name_input:
            return
        self.name_input.setText(scenario.name)
        self._suppress_geo_autofill = True
        self._set_location_from_scenario(scenario)
        self._suppress_geo_autofill = False
        if self.hazard_combo is not None:
            index = self.hazard_combo.findData(scenario.hazard_profile.hazard_type)
            self.hazard_combo.setCurrentIndex(index)
        self.severity_input.setText(scenario.hazard_profile.severity_band)
        self.duration_input.setValue(scenario.hazard_profile.duration_days)
        self.infrastructure_damage_input.setValue(scenario.hazard_profile.infrastructure_damage_percent)
        self.total_population_input.setValue(scenario.population_profile.total_population)
        self.displaced_population_input.setValue(scenario.population_profile.displaced_population)
        self.children_input.setValue(scenario.population_profile.children_under_five)
        self.older_adults_input.setValue(scenario.population_profile.older_adults)
        self.pregnant_input.setValue(scenario.population_profile.pregnant_or_lactating_people)
        self.medically_vulnerable_input.setValue(scenario.population_profile.medically_vulnerable_population)
        self.road_access_input.setValue(scenario.infrastructure_profile.road_access_score)
        self.health_operability_input.setValue(scenario.infrastructure_profile.health_facility_operability_score)
        self.water_availability_input.setValue(scenario.infrastructure_profile.local_water_availability_liters_per_day)
        self.food_supply_ratio_input.setValue(scenario.infrastructure_profile.local_food_supply_ratio)
        self.notes_input.setPlainText(scenario.notes)
        self._populate_resources_table(scenario.resources)
        self._populate_personnel_table(scenario.personnel)
        self._populate_transport_table(scenario.transportation)
        self._apply_editor_lock_state()

    def _populate_resources_table(self, resources: tuple[InventoryPosition, ...]) -> None:
        if self.resource_table is None:
            return
        self.resource_table.setRowCount(0)
        for resource in resources:
            self._insert_row(
                self.resource_table,
                [
                    resource.name,
                    resource.category,
                    str(resource.quantity),
                    resource.unit,
                    str(resource.priority_rank),
                ],
            )

    def _populate_personnel_table(self, personnel: tuple[PersonnelRole, ...]) -> None:
        if self.personnel_table is None:
            return
        self.personnel_table.setRowCount(0)
        for role in personnel:
            self._insert_row(
                self.personnel_table,
                [
                    role.name,
                    str(role.count),
                    str(role.shift_hours),
                    str(role.hourly_cost),
                    str(role.volunteers),
                ],
            )

    def _populate_transport_table(self, transportation: tuple[TransportAsset, ...]) -> None:
        if self.transport_table is None:
            return
        self.transport_table.setRowCount(0)
        for asset in transportation:
            self._insert_row(
                self.transport_table,
                [
                    asset.name,
                    str(asset.capacity_kg),
                    str(asset.quantity),
                    str(asset.speed_kmh),
                    str(asset.reliability_score),
                    str(asset.cost_per_km),
                ],
            )

    def _build_scenario_from_editor(self) -> Scenario:
        hazard_type = self.hazard_combo.currentData() if self.hazard_combo is not None else HazardType.FLOOD
        if not isinstance(hazard_type, HazardType):
            hazard_type = HazardType.FLOOD

        resources = self._read_resources_from_table()
        personnel = self._read_personnel_from_table()
        transportation = self._read_transport_from_table()

        return replace(
            self.active_scenario,
            name=self.name_input.text().strip() or self.active_scenario.name,
            world_region=self._selected_world_region(),
            country=self._selected_country(),
            region=self._selected_region(),
            latitude=self.latitude_input.value() if self.latitude_input is not None else None,
            longitude=self.longitude_input.value() if self.longitude_input is not None else None,
            hazard_profile=HazardProfile(
                hazard_type=hazard_type,
                severity_band=self.severity_input.text().strip() or "moderate",
                duration_days=self.duration_input.value(),
                location_label=self._current_location_label(),
                infrastructure_damage_percent=self.infrastructure_damage_input.value(),
            ),
            population_profile=PopulationProfile(
                total_population=self.total_population_input.value(),
                displaced_population=self.displaced_population_input.value(),
                children_under_five=self.children_input.value(),
                older_adults=self.older_adults_input.value(),
                pregnant_or_lactating_people=self.pregnant_input.value(),
                medically_vulnerable_population=self.medically_vulnerable_input.value(),
            ),
            infrastructure_profile=InfrastructureProfile(
                road_access_score=self.road_access_input.value(),
                health_facility_operability_score=self.health_operability_input.value(),
                local_water_availability_liters_per_day=self.water_availability_input.value(),
                local_food_supply_ratio=self.food_supply_ratio_input.value(),
            ),
            resources=resources,
            personnel=personnel,
            transportation=transportation,
            notes=self.notes_input.toPlainText().strip(),
        )

    def _set_location_from_scenario(self, scenario: Scenario) -> None:
        if self.world_region_combo is None or self.country_combo is None or self.region_combo is None:
            return

        world_region = scenario.world_region
        country = scenario.country
        region = scenario.region
        if not country or not region:
            parsed_country, parsed_region = parse_location_label(scenario.hazard_profile.location_label)
            country = country or parsed_country
            region = region or parsed_region

        if world_region is None and country:
            world_region = get_world_region_for_country(country)

        if world_region is None:
            world_region = self.world_region_combo.itemText(0) if self.world_region_combo.count() else ""
        self._sync_countries_for_world_region(world_region)

        world_region_index = self.world_region_combo.findText(world_region)
        if world_region_index >= 0:
            self.world_region_combo.setCurrentIndex(world_region_index)
            self._sync_countries_for_world_region(world_region)

        if country is None:
            country = self.country_combo.itemText(0) if self.country_combo.count() else ""
        self._sync_regions_for_country(country)

        country_index = self.country_combo.findText(country)
        if country_index >= 0:
            self.country_combo.setCurrentIndex(country_index)
            self._sync_regions_for_country(country)

        if region:
            region_index = self.region_combo.findText(region)
            if region_index >= 0:
                self.region_combo.setCurrentIndex(region_index)

        profile = get_region_profile(self._selected_country(), self._selected_region())
        if self.latitude_input is not None:
            if scenario.latitude is not None:
                self.latitude_input.setValue(scenario.latitude)
            elif profile is not None:
                self.latitude_input.setValue(profile.latitude)
        if self.longitude_input is not None:
            if scenario.longitude is not None:
                self.longitude_input.setValue(scenario.longitude)
            elif profile is not None:
                self.longitude_input.setValue(profile.longitude)
        self._refresh_map_location_preview()

    def _selected_country(self) -> str | None:
        if self.country_combo is None:
            return None
        value = self.country_combo.currentText().strip()
        return value or None

    def _selected_region(self) -> str | None:
        if self.region_combo is None:
            return None
        value = self.region_combo.currentText().strip()
        return value or None

    def _selected_world_region(self) -> str | None:
        if self.world_region_combo is None:
            return None
        value = self.world_region_combo.currentText().strip()
        return value or None

    def _enable_combo_search(self, combo: QComboBox) -> None:
        combo.setEditable(True)
        combo.setInsertPolicy(QComboBox.NoInsert)
        combo.setMaxVisibleItems(15)
        completer = combo.completer()
        if completer is None:
            completer = QCompleter(combo.model(), combo)
            combo.setCompleter(completer)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setFilterMode(Qt.MatchContains)
        completer.setCompletionMode(QCompleter.PopupCompletion)

    def _sync_countries_for_world_region(self, world_region: str) -> None:
        if self.country_combo is None:
            return
        current_country = self.country_combo.currentText()
        self.country_combo.blockSignals(True)
        self.country_combo.clear()
        for country in list_countries_for_world_region(world_region):
            self.country_combo.addItem(country)
        if self.country_combo.count() > 0:
            index = self.country_combo.findText(current_country)
            self.country_combo.setCurrentIndex(index if index >= 0 else 0)
        self.country_combo.blockSignals(False)
        selected_country = self._selected_country()
        if selected_country:
            self._sync_regions_for_country(selected_country)

    def _on_world_region_changed(self) -> None:
        world_region = self._selected_world_region()
        if world_region is None:
            return
        self._sync_countries_for_world_region(world_region)
        self._on_country_changed()

    def _sync_regions_for_country(self, country: str) -> None:
        if self.region_combo is None:
            return
        current_region = self.region_combo.currentText()
        self.region_combo.blockSignals(True)
        self.region_combo.clear()
        for region in list_regions(country):
            self.region_combo.addItem(region)
        if self.region_combo.count() > 0:
            index = self.region_combo.findText(current_region)
            self.region_combo.setCurrentIndex(index if index >= 0 else 0)
        self.region_combo.blockSignals(False)

    def _on_country_changed(self) -> None:
        country = self._selected_country()
        if country is None:
            return
        if self.world_region_combo is not None:
            expected_world_region = get_world_region_for_country(country)
            if expected_world_region is not None:
                world_index = self.world_region_combo.findText(expected_world_region)
                if world_index >= 0 and self.world_region_combo.currentIndex() != world_index:
                    self.world_region_combo.blockSignals(True)
                    self.world_region_combo.setCurrentIndex(world_index)
                    self.world_region_combo.blockSignals(False)
        self._sync_regions_for_country(country)
        self._on_region_changed()

    def _on_region_changed(self) -> None:
        if self._suppress_geo_autofill:
            return
        country = self._selected_country()
        region = self._selected_region()
        if country is None or region is None:
            return
        profile = get_region_profile(country, region)
        if profile is None:
            return
        self.infrastructure_damage_input.setValue(profile.infrastructure_damage_percent)
        self.road_access_input.setValue(profile.road_access_score)
        self.health_operability_input.setValue(profile.health_operability_score)
        self.water_availability_input.setValue(profile.local_water_liters_per_day)
        self.food_supply_ratio_input.setValue(profile.local_food_supply_ratio)
        if self.latitude_input is not None:
            self.latitude_input.setValue(profile.latitude)
        if self.longitude_input is not None:
            self.longitude_input.setValue(profile.longitude)
        self._refresh_map_location_preview()
        self._refresh_validation_banner()
        self.statusBar().showMessage(
            f"Applied regional profile: {country} / {region}"
        )

    def _current_location_label(self) -> str:
        return format_location_label(self._selected_country(), self._selected_region())

    def _read_resources_from_table(self) -> tuple[InventoryPosition, ...]:
        if self.resource_table is None:
            return ()
        items: list[InventoryPosition] = []
        for row in range(self.resource_table.rowCount()):
            name = self._table_text(self.resource_table, row, 0, "Resource")
            category = self._table_text(self.resource_table, row, 1, "water")
            quantity = self._to_float(self._table_text(self.resource_table, row, 2, "0"), 0.0)
            unit = self._table_text(self.resource_table, row, 3, "liters")
            priority = self._to_int(self._table_text(self.resource_table, row, 4, "1"), 1)
            items.append(
                InventoryPosition(
                    name=name,
                    category=category,
                    quantity=quantity,
                    unit=unit,
                    priority_rank=priority,
                )
            )
        return tuple(items)

    def _read_personnel_from_table(self) -> tuple[PersonnelRole, ...]:
        if self.personnel_table is None:
            return ()
        items: list[PersonnelRole] = []
        for row in range(self.personnel_table.rowCount()):
            name = self._table_text(self.personnel_table, row, 0, "Role")
            count = self._to_int(self._table_text(self.personnel_table, row, 1, "0"), 0)
            shift_hours = self._to_float(self._table_text(self.personnel_table, row, 2, "8"), 8.0)
            hourly_cost = self._to_float(self._table_text(self.personnel_table, row, 3, "0"), 0.0)
            volunteers = self._to_int(self._table_text(self.personnel_table, row, 4, "0"), 0)
            items.append(
                PersonnelRole(
                    name=name,
                    count=count,
                    shift_hours=shift_hours,
                    hourly_cost=hourly_cost,
                    volunteers=volunteers,
                )
            )
        return tuple(items)

    def _read_transport_from_table(self) -> tuple[TransportAsset, ...]:
        if self.transport_table is None:
            return ()
        items: list[TransportAsset] = []
        for row in range(self.transport_table.rowCount()):
            name = self._table_text(self.transport_table, row, 0, "Asset")
            capacity_kg = self._to_float(self._table_text(self.transport_table, row, 1, "0"), 0.0)
            quantity = self._to_int(self._table_text(self.transport_table, row, 2, "1"), 1)
            speed_kmh = self._to_float(self._table_text(self.transport_table, row, 3, "40"), 40.0)
            reliability_score = self._to_float(self._table_text(self.transport_table, row, 4, "0.8"), 0.8)
            cost_per_km = self._to_float(self._table_text(self.transport_table, row, 5, "0"), 0.0)
            items.append(
                TransportAsset(
                    name=name,
                    capacity_kg=capacity_kg,
                    quantity=quantity,
                    speed_kmh=speed_kmh,
                    reliability_score=max(0.0, min(reliability_score, 1.0)),
                    cost_per_km=cost_per_km,
                )
            )
        return tuple(items)

    def _table_text(self, table: QTableWidget, row: int, col: int, fallback: str) -> str:
        item = table.item(row, col)
        if item is None:
            return fallback
        value = item.text().strip()
        return value if value else fallback

    def _to_float(self, raw: str, fallback: float) -> float:
        try:
            return float(raw)
        except ValueError:
            return fallback

    def _to_int(self, raw: str, fallback: int) -> int:
        try:
            return int(float(raw))
        except ValueError:
            return fallback

    def _create_new_scenario(self) -> None:
        scenario = self.scenario_repository.save_scenario(build_default_scenario())
        self.active_scenario = scenario
        self._populate_editor_from_scenario(scenario)
        self._refresh_validation_banner()
        self._refresh_scenario_list(selected_scenario_id=scenario.scenario_id)
        self.statusBar().showMessage(f"Created new scenario: {scenario.name}")
        self._run_analysis()

    def _branch_variant(self) -> None:
        variant_label, ok = QInputDialog.getText(
            self,
            "Branch Variant",
            "Variant label:",
            text="what-if",
        )
        if not ok:
            return
        variant_label = variant_label.strip()
        if not variant_label:
            QMessageBox.warning(self, "Invalid Variant Label", "Variant label cannot be empty.")
            return

        if self._is_locked(self.active_scenario) and not self._is_root_baseline(self.active_scenario):
            QMessageBox.warning(
                self,
                "Branch Not Allowed",
                "Locked non-baseline scenarios cannot be branched until unlocked.",
            )
            return

        if self._is_locked_baseline(self.active_scenario):
            source_scenario = self.active_scenario
        else:
            source_scenario = self._build_scenario_from_editor()
            self.active_scenario = self.scenario_repository.save_scenario(source_scenario)
        variant = self.scenario_repository.branch_variant(
            source_scenario.scenario_id,
            variant_label=variant_label,
        )
        if variant is None:
            QMessageBox.warning(self, "Variant Error", "Unable to create scenario variant.")
            return

        self.active_scenario = variant
        self._populate_editor_from_scenario(variant)
        self._refresh_scenario_list(selected_scenario_id=variant.scenario_id)
        self.statusBar().showMessage(f"Created variant: {variant.name}")
        self._run_analysis()

    def _lock_baseline(self) -> None:
        scenario = self._build_scenario_from_editor()
        is_baseline = scenario.variant_label == "baseline" and scenario.base_scenario_id is None
        if not is_baseline:
            QMessageBox.warning(
                self,
                "Lock Not Allowed",
                "Only root baseline scenarios can be locked.",
            )
            return
        if scenario.status == ScenarioStatus.LOCKED:
            QMessageBox.information(self, "Already Locked", "Baseline scenario is already locked.")
            return

        self.active_scenario = self.scenario_repository.save_scenario(
            replace(scenario, status=ScenarioStatus.LOCKED)
        )
        self._populate_editor_from_scenario(self.active_scenario)
        self._refresh_scenario_list(selected_scenario_id=self.active_scenario.scenario_id)
        self.statusBar().showMessage(f"Baseline locked: {self.active_scenario.name}")

    def _save_active_scenario(self) -> None:
        if self._is_locked(self.active_scenario):
            QMessageBox.warning(
                self,
                "Scenario Locked",
                "This scenario is locked. Branch a variant to make changes.",
            )
            return

        scenario = self._build_scenario_from_editor()
        issues = self._validate_scenario(scenario)
        self._set_validation_issues(issues)
        if issues:
            QMessageBox.warning(
                self,
                "Validation Required",
                issues[0],
            )
            return

        self.active_scenario = self.scenario_repository.save_scenario(scenario)
        if self.change_preview is not None:
            self.change_preview.setPlainText("No pending differences from saved scenario.")
        self._refresh_scenario_list(selected_scenario_id=self.active_scenario.scenario_id)
        self.statusBar().showMessage(f"Saved scenario: {self.active_scenario.name}")

    def _run_analysis(self) -> None:
        scenario = self._build_scenario_from_editor()
        issues = self._validate_scenario(scenario)
        self._set_validation_issues(issues)
        if issues:
            QMessageBox.warning(
                self,
                "Validation Required",
                issues[0],
            )
            return
        self.active_scenario = scenario
        self.initial_analysis = self.planning_engine.analyze(self.active_scenario)
        self._update_summary_panel(self.initial_analysis)
        self._update_results_view(self.initial_analysis)
        self._refresh_map_tab(self.active_scenario, self.initial_analysis)
        self.statusBar().showMessage(f"Analysis updated for scenario: {self.active_scenario.name}")

    def _load_selected_scenario(self) -> None:
        if self.scenario_list_widget is None:
            return
        items = self.scenario_list_widget.selectedItems()
        if not items:
            return
        scenario_id = items[0].data(Qt.UserRole)
        if not isinstance(scenario_id, str):
            return

        scenario = self.scenario_repository.get_scenario(scenario_id)
        if scenario is None:
            return

        self.active_scenario = scenario
        self.initial_analysis = self.planning_engine.analyze(self.active_scenario)
        self._populate_editor_from_scenario(self.active_scenario)
        self._refresh_validation_banner()
        self._update_summary_panel(self.initial_analysis)
        self._update_results_view(self.initial_analysis)
        self._refresh_map_tab(self.active_scenario, self.initial_analysis)
        self.statusBar().showMessage(f"Loaded scenario: {self.active_scenario.name}")

    def _validate_scenario(self, scenario: Scenario) -> list[str]:
        issues: list[str] = []
        if scenario.population_profile.total_population <= 0:
            issues.append("Total population must be greater than zero.")
        if scenario.population_profile.displaced_population > scenario.population_profile.total_population:
            issues.append("Displaced population cannot exceed total population.")
        if scenario.world_region is None:
            issues.append("Select a world region to narrow crisis context.")
        if scenario.country is None or scenario.region is None:
            issues.append("Select both country and region for location-aware assumptions.")
        if scenario.hazard_profile.duration_days <= 0:
            issues.append("Duration must be at least one day.")
        return issues

    def _set_validation_issues(self, issues: list[str]) -> None:
        if self.validation_banner is None:
            return
        if issues:
            self.validation_banner.setText("Validation checks: " + " | ".join(issues))
            self.validation_banner.show()
        else:
            self.validation_banner.hide()

    def _refresh_validation_banner(self) -> None:
        scenario = self._build_scenario_from_editor()
        self._set_validation_issues(self._validate_scenario(scenario))

    def _preview_changes(self) -> None:
        if self.change_preview is None:
            return
        draft = self._build_scenario_from_editor()
        self._set_validation_issues(self._validate_scenario(draft))
        lines: list[str] = ["Pending changes vs active scenario:"]

        def add_change(label: str, old: object, new: object) -> None:
            if old != new:
                lines.append(f"- {label}: {old} -> {new}")

        add_change("Name", self.active_scenario.name, draft.name)
        add_change("Country", self.active_scenario.country, draft.country)
        add_change("Region", self.active_scenario.region, draft.region)
        add_change("Latitude", self.active_scenario.latitude, draft.latitude)
        add_change("Longitude", self.active_scenario.longitude, draft.longitude)
        add_change("Hazard", self.active_scenario.hazard_profile.hazard_type.value, draft.hazard_profile.hazard_type.value)
        add_change("Severity", self.active_scenario.hazard_profile.severity_band, draft.hazard_profile.severity_band)
        add_change("Duration days", self.active_scenario.hazard_profile.duration_days, draft.hazard_profile.duration_days)
        add_change(
            "Displaced population",
            self.active_scenario.population_profile.displaced_population,
            draft.population_profile.displaced_population,
        )
        add_change(
            "Infrastructure damage %",
            self.active_scenario.hazard_profile.infrastructure_damage_percent,
            draft.hazard_profile.infrastructure_damage_percent,
        )
        add_change("Resource rows", len(self.active_scenario.resources), len(draft.resources))
        add_change("Personnel rows", len(self.active_scenario.personnel), len(draft.personnel))
        add_change("Transport rows", len(self.active_scenario.transportation), len(draft.transportation))

        if len(lines) == 1:
            lines.append("- No pending changes.")
        self.change_preview.setPlainText("\n".join(lines))

    def _open_compare_tab(self) -> None:
        if self.workspace_tabs is None or self.compare_tab_index is None:
            return
        self.workspace_tabs.setCurrentIndex(self.compare_tab_index)

    def _run_comparison(self) -> None:
        if self.compare_left_combo is None or self.compare_right_combo is None or self.compare_output is None:
            return
        profile = self.comparison_profile_combo.currentText() if self.comparison_profile_combo else "Balanced"
        metric_filter = self.metric_filter_combo.currentText() if self.metric_filter_combo else "All Metrics"
        profile_weights = self._comparison_profile_weights(profile)

        left_id = self.compare_left_combo.currentData()
        right_id = self.compare_right_combo.currentData()
        if not isinstance(left_id, str) or not isinstance(right_id, str):
            return
        if left_id == right_id:
            self.compare_output.setPlainText("Choose two different scenarios to compare.")
            return

        left_scenario = self.scenario_repository.get_scenario(left_id)
        right_scenario = self.scenario_repository.get_scenario(right_id)
        if left_scenario is None or right_scenario is None:
            self.compare_output.setPlainText("Unable to load one or both scenarios for comparison.")
            return

        left_analysis = self.planning_engine.analyze(left_scenario)
        right_analysis = self.planning_engine.analyze(right_scenario)
        winner = self._comparison_winner(left_analysis, right_analysis, profile)

        critical_delta = right_analysis.critical_coverage_percent - left_analysis.critical_coverage_percent
        overall_delta = right_analysis.overall_coverage_percent - left_analysis.overall_coverage_percent
        cost_delta = right_analysis.total_estimated_cost - left_analysis.total_estimated_cost
        delivery_days_delta = self._metadata_delta(
            left_analysis,
            right_analysis,
            "transport_estimated_delivery_days",
        )
        daily_capacity_delta = self._metadata_delta(
            left_analysis,
            right_analysis,
            "transport_daily_movable_capacity_kg",
        )
        self._update_compare_kpis(
            critical_delta,
            overall_delta,
            cost_delta,
            delivery_days_delta,
            daily_capacity_delta,
            winner,
        )

        left_lineage = self.scenario_repository.get_lineage(left_scenario.scenario_id)
        right_lineage = self.scenario_repository.get_lineage(right_scenario.scenario_id)

        output_text = build_comparison_output_text(
            left_scenario=left_scenario,
            right_scenario=right_scenario,
            left_analysis=left_analysis,
            right_analysis=right_analysis,
            profile=profile,
            profile_weights=profile_weights,
            metric_filter=metric_filter,
            winner=winner,
            lineage_left=self._format_lineage(left_lineage),
            lineage_right=self._format_lineage(right_lineage),
        )

        self.last_comparison_payload = {
            "left_scenario": left_scenario,
            "right_scenario": right_scenario,
            "left_analysis": left_analysis,
            "right_analysis": right_analysis,
            "profile": profile,
            "profile_weights": profile_weights,
            "metric_filter": metric_filter,
            "winner": winner,
            "lineage_left": self._format_lineage(left_lineage),
            "lineage_right": self._format_lineage(right_lineage),
        }
        self.compare_output.setPlainText(output_text)

    def _swap_comparison_selection(self) -> None:
        if self.compare_left_combo is None or self.compare_right_combo is None:
            return
        left_index = self.compare_left_combo.currentIndex()
        right_index = self.compare_right_combo.currentIndex()
        self.compare_left_combo.setCurrentIndex(right_index)
        self.compare_right_combo.setCurrentIndex(left_index)
        self._run_comparison()

    def _format_lineage(self, lineage: list) -> str:
        if not lineage:
            return "Unknown"
        return " -> ".join(f"{entry.name} [{entry.variant_label}]" for entry in lineage)

    def _comparison_winner(self, left: AnalysisSummary, right: AnalysisSummary, profile: str) -> str:
        weights = self._comparison_profile_weights(profile)
        critical_weight = weights["critical"]
        overall_weight = weights["overall"]
        cost_weight = weights["cost"]

        left_score = (left.critical_coverage_percent * critical_weight) + (left.overall_coverage_percent * overall_weight) - (left.total_estimated_cost * cost_weight)
        right_score = (right.critical_coverage_percent * critical_weight) + (right.overall_coverage_percent * overall_weight) - (right.total_estimated_cost * cost_weight)
        if abs(left_score - right_score) < 0.01:
            return "Equivalent planning score across selected metrics."
        return "Scenario B leads selected metrics." if right_score > left_score else "Scenario A leads selected metrics."

    def _comparison_profile_weights(self, profile: str) -> dict[str, float]:
        if profile == "Coverage First":
            return {"critical": 3.0, "overall": 1.5, "cost": 1 / 20000}
        if profile == "Cost First":
            return {"critical": 1.5, "overall": 1.0, "cost": 1 / 5000}
        return {"critical": 2.0, "overall": 1.0, "cost": 1 / 10000}

    def _metadata_delta(self, left: AnalysisSummary, right: AnalysisSummary, key: str) -> float | None:
        left_value = left.metadata.get(key)
        right_value = right.metadata.get(key)
        if isinstance(left_value, (int, float)) and isinstance(right_value, (int, float)):
            return float(right_value - left_value)
        return None

    def _branch_selected_tree_node(self) -> None:
        selected_id = self._selected_tree_scenario_id()
        if selected_id is None:
            QMessageBox.information(self, "Branch Variant", "Select a scenario node in the branch tree first.")
            return

        variant_label, ok = QInputDialog.getText(self, "Branch Selected", "Variant label:", text="branch")
        if not ok:
            return
        variant_label = variant_label.strip()
        if not variant_label:
            QMessageBox.warning(self, "Invalid Variant Label", "Variant label cannot be empty.")
            return

        selected_scenario = self.scenario_repository.get_scenario(selected_id)
        if selected_scenario is None:
            QMessageBox.warning(self, "Branch Error", "Selected scenario could not be loaded.")
            return
        if selected_scenario.status == ScenarioStatus.LOCKED and not self._is_root_baseline(selected_scenario):
            QMessageBox.warning(
                self,
                "Branch Not Allowed",
                "Only locked root baselines can be branched. Unlock this scenario first.",
            )
            return

        variant = self.scenario_repository.branch_variant(selected_id, variant_label)
        if variant is None:
            QMessageBox.warning(self, "Branch Error", "Unable to branch selected scenario.")
            return

        self.active_scenario = variant
        self._populate_editor_from_scenario(variant)
        self._refresh_scenario_list(selected_scenario_id=variant.scenario_id)
        self.statusBar().showMessage(f"Branched from tree: {variant.name}")
        self._run_analysis()

    def _compare_selected_with_active(self) -> None:
        selected_id = self._selected_tree_scenario_id()
        if selected_id is None:
            QMessageBox.information(self, "Compare", "Select a scenario node in the branch tree first.")
            return
        if self.compare_left_combo is None or self.compare_right_combo is None:
            return

        left_index = self.compare_left_combo.findData(self.active_scenario.scenario_id)
        right_index = self.compare_right_combo.findData(selected_id)
        if left_index >= 0:
            self.compare_left_combo.setCurrentIndex(left_index)
        if right_index >= 0:
            self.compare_right_combo.setCurrentIndex(right_index)
        self._run_comparison()

    def _lock_selected_tree_node(self) -> None:
        selected_id = self._selected_tree_scenario_id()
        if selected_id is None:
            QMessageBox.information(self, "Lock Scenario", "Select a scenario in the branch tree first.")
            return

        scenario = self.scenario_repository.get_scenario(selected_id)
        if scenario is None:
            QMessageBox.warning(self, "Lock Scenario", "Selected scenario could not be loaded.")
            return
        if not self._is_root_baseline(scenario):
            QMessageBox.warning(self, "Lock Not Allowed", "Only root baseline scenarios can be locked.")
            return

        updated = self.scenario_repository.update_scenario_status(selected_id, ScenarioStatus.LOCKED)
        if updated is None:
            QMessageBox.warning(self, "Lock Error", "Unable to lock selected scenario.")
            return

        if self.active_scenario.scenario_id == updated.scenario_id:
            self.active_scenario = updated
            self._populate_editor_from_scenario(updated)
        self._refresh_scenario_list(selected_scenario_id=updated.scenario_id)
        self.statusBar().showMessage(f"Locked baseline from tree: {updated.name}")

    def _unlock_selected_tree_node(self) -> None:
        selected_id = self._selected_tree_scenario_id()
        if selected_id is None:
            QMessageBox.information(self, "Unlock Scenario", "Select a scenario in the branch tree first.")
            return

        scenario = self.scenario_repository.get_scenario(selected_id)
        if scenario is None:
            QMessageBox.warning(self, "Unlock Scenario", "Selected scenario could not be loaded.")
            return
        if not self._is_root_baseline(scenario):
            QMessageBox.warning(self, "Unlock Not Allowed", "Only root baseline scenarios can be unlocked.")
            return

        updated = self.scenario_repository.update_scenario_status(selected_id, ScenarioStatus.DRAFT)
        if updated is None:
            QMessageBox.warning(self, "Unlock Error", "Unable to unlock selected scenario.")
            return

        if self.active_scenario.scenario_id == updated.scenario_id:
            self.active_scenario = updated
            self._populate_editor_from_scenario(updated)
        self._refresh_scenario_list(selected_scenario_id=updated.scenario_id)
        self.statusBar().showMessage(f"Unlocked baseline from tree: {updated.name}")

    def _selected_tree_scenario_id(self) -> str | None:
        if self.lineage_tree is None:
            return None
        item = self.lineage_tree.currentItem()
        if item is None:
            return None
        value = item.data(0, Qt.UserRole)
        return value if isinstance(value, str) else None

    def _is_locked_baseline(self, scenario: Scenario) -> bool:
        return (
            scenario.variant_label == "baseline"
            and scenario.base_scenario_id is None
            and scenario.status == ScenarioStatus.LOCKED
        )

    def _is_root_baseline(self, scenario: Scenario) -> bool:
        return scenario.variant_label == "baseline" and scenario.base_scenario_id is None

    def _is_locked(self, scenario: Scenario) -> bool:
        return scenario.status == ScenarioStatus.LOCKED

    def _update_compare_kpis(
        self,
        critical_delta: float,
        overall_delta: float,
        cost_delta: float,
        delivery_days_delta: float | None,
        daily_capacity_delta: float | None,
        winner: str,
    ) -> None:
        if not self.compare_kpi_labels:
            return
        self.compare_kpi_labels["critical_delta"].setText(f"Critical delta: {critical_delta:+.1f}%")
        self.compare_kpi_labels["overall_delta"].setText(f"Overall delta: {overall_delta:+.1f}%")
        self.compare_kpi_labels["cost_delta"].setText(f"Cost delta: ${cost_delta:+,.2f}")
        if delivery_days_delta is None:
            self.compare_kpi_labels["delivery_days_delta"].setText("Delivery days delta: n/a")
        else:
            self.compare_kpi_labels["delivery_days_delta"].setText(f"Delivery days delta: {delivery_days_delta:+.2f}")
        if daily_capacity_delta is None:
            self.compare_kpi_labels["daily_capacity_delta"].setText("Daily capacity delta: n/a")
        else:
            self.compare_kpi_labels["daily_capacity_delta"].setText(f"Daily capacity delta: {daily_capacity_delta:+,.2f} kg")
        self.compare_kpi_labels["winner"].setText(f"Winner: {winner}")

    def _apply_editor_lock_state(self) -> None:
        enabled = not self._is_locked(self.active_scenario)
        for widget in self.editor_inputs:
            widget.setEnabled(enabled)
        if self.resource_table is not None:
            self.resource_table.setEnabled(enabled)
        if self.personnel_table is not None:
            self.personnel_table.setEnabled(enabled)
        if self.transport_table is not None:
            self.transport_table.setEnabled(enabled)
        for button in (
            self.resource_add_button,
            self.resource_remove_button,
            self.personnel_add_button,
            self.personnel_remove_button,
            self.transport_add_button,
            self.transport_remove_button,
            self.save_button,
        ):
            if button is not None:
                button.setEnabled(enabled)

    def _update_summary_panel(self, analysis: AnalysisSummary) -> None:
        self.summary_labels["critical"].setText(f"{analysis.critical_coverage_percent}%")
        self.summary_labels["overall"].setText(f"{analysis.overall_coverage_percent}%")
        self.summary_labels["cost"].setText(f"${analysis.total_estimated_cost:,.2f}")
        self.summary_labels["confidence"].setText(analysis.confidence_level.value.title())
        if analysis.risk_flags:
            self.summary_labels["risks"].setText("\n".join(f"• {flag.title}" for flag in analysis.risk_flags))
        else:
            self.summary_labels["risks"].setText("No active risk flags")

    def _update_results_view(self, analysis: AnalysisSummary) -> None:
        if self.results_notes is None:
            return
        lines = [
            "Planning Summary",
            f"- Critical coverage: {analysis.critical_coverage_percent:.1f}%",
            f"- Overall coverage: {analysis.overall_coverage_percent:.1f}%",
            f"- Estimated total cost: ${analysis.total_estimated_cost:,.2f}",
            f"- Confidence: {analysis.confidence_level.value.title()}",
            "",
            "Computed Metrics",
        ]
        for key, value in sorted(analysis.metadata.items()):
            lines.append(f"- {self._format_metric_key(key)}: {self._format_metric_value(value)}")
        lines.append("")
        lines.append("Unmet Critical Needs")
        if analysis.unmet_critical_needs:
            lines.extend(f"- {item}" for item in analysis.unmet_critical_needs)
        else:
            lines.append("- None")
        lines.append("")
        lines.append("Assumptions Trace")
        lines.extend(f"- {identifier}" for identifier in analysis.assumptions_trace)
        self.results_notes.setPlainText("\n".join(lines))

    def _refresh_map_location_preview(self) -> None:
        if self.map_canvas is None or self.latitude_input is None or self.longitude_input is None:
            return
        self.map_canvas.set_location(
            self.latitude_input.value(),
            self.longitude_input.value(),
            self._current_location_label(),
        )

    def _on_timeline_day_changed(self, value: int) -> None:
        if self.timeline_day_label is not None:
            self.timeline_day_label.setText(f"Day {value}")
        self._refresh_timeline_summary()

    def _refresh_map_tab(self, scenario: Scenario, analysis: AnalysisSummary) -> None:
        if self.map_canvas is None:
            return

        self.map_canvas.set_location(scenario.latitude, scenario.longitude, scenario.hazard_profile.location_label)

        if self.timeline_slider is not None:
            previous_day = self.timeline_slider.value()
            max_day = max(1, scenario.hazard_profile.duration_days)
            self.timeline_slider.blockSignals(True)
            self.timeline_slider.setRange(1, max_day)
            self.timeline_slider.setValue(min(previous_day, max_day))
            self.timeline_slider.blockSignals(False)
            if self.timeline_day_label is not None:
                self.timeline_day_label.setText(f"Day {self.timeline_slider.value()}")

        self._refresh_timeline_summary(analysis)

    def _refresh_timeline_summary(self, analysis: AnalysisSummary | None = None) -> None:
        if self.timeline_summary is None or self.timeline_slider is None:
            return
        reference_analysis = analysis if analysis is not None else self.initial_analysis
        lines = build_timeline_projection_lines(
            self.active_scenario,
            reference_analysis,
            self.timeline_slider.value(),
        )
        self.timeline_summary.setPlainText("\n".join(lines))

    def _format_metric_key(self, key: str) -> str:
        words = key.replace("_", " ").strip().split()
        return " ".join(word.capitalize() for word in words)

    def _format_metric_value(self, value: object) -> str:
        if isinstance(value, float):
            return f"{value:,.2f}"
        if isinstance(value, int):
            return f"{value:,}"
        return str(value)

    def _copy_comparison_output(self) -> None:
        if self.compare_output is None:
            return
        text = self.compare_output.toPlainText().strip()
        if not text:
            self.statusBar().showMessage("No comparison summary to copy.")
            return
        QApplication.clipboard().setText(text)
        self.statusBar().showMessage("Comparison summary copied to clipboard.")

    def _export_active_report(self) -> None:
        analysis = self.planning_engine.analyze(self.active_scenario)
        timeline_day = self.timeline_slider.value() if self.timeline_slider is not None else 1
        report_text = build_scenario_report(self.active_scenario, analysis, timeline_day=timeline_day)

        output_path = write_text_report(
            self.config.export_directory,
            prefix=f"scenario_report_{self.active_scenario.variant_label}",
            content=report_text,
        )
        self.statusBar().showMessage(f"Exported scenario report: {output_path}")

    def _export_comparison_report(self) -> None:
        if self.last_comparison_payload is None:
            return

        payload = self.last_comparison_payload
        report_text = build_comparison_report(
            left_scenario=payload["left_scenario"],
            right_scenario=payload["right_scenario"],
            left_analysis=payload["left_analysis"],
            right_analysis=payload["right_analysis"],
            profile=payload["profile"],
            profile_weights=payload["profile_weights"],
            metric_filter=payload["metric_filter"],
            winner=payload["winner"],
            lineage_left=payload["lineage_left"],
            lineage_right=payload["lineage_right"],
            timeline_day=self.timeline_slider.value() if self.timeline_slider is not None else 1,
        )

        output_path = write_text_report(
            self.config.export_directory,
            prefix="comparison_report",
            content=report_text,
        )
        self.statusBar().showMessage(f"Exported comparison report: {output_path}")