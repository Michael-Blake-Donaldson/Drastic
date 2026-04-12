from __future__ import annotations

from dataclasses import replace

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QComboBox,
    QDockWidget,
    QDoubleSpinBox,
    QFormLayout,
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
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
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
from services.scenario_factory import build_default_scenario


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
        self.summary_labels: dict[str, QLabel] = {}
        self.results_notes: QTextEdit | None = None

        self.name_input: QLineEdit | None = None
        self.location_input: QLineEdit | None = None
        self.notes_input: QTextEdit | None = None
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
        self.compare_output: QTextEdit | None = None
        self.compare_tab_index: int | None = None
        self.editor_inputs: list[QWidget] = []
        self.resource_add_button: QPushButton | None = None
        self.resource_remove_button: QPushButton | None = None
        self.personnel_add_button: QPushButton | None = None
        self.personnel_remove_button: QPushButton | None = None
        self.transport_add_button: QPushButton | None = None
        self.transport_remove_button: QPushButton | None = None
        self.save_button: QPushButton | None = None

        self.setWindowTitle("DRASTIC Planner")
        self.resize(1480, 920)

        self._build_toolbar()
        self._build_left_navigation()
        self._build_summary_dock()
        self._build_central_workspace()
        self.setStatusBar(QStatusBar(self))
        self.statusBar().showMessage(f"Offline-first mode enabled • Database: {self.config.database_path}")

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
        toolbar.addAction(export_action)

    def _build_left_navigation(self) -> None:
        navigation_dock = QDockWidget("Scenarios", self)
        navigation_dock.setAllowedAreas(Qt.LeftDockWidgetArea)

        scenario_list = QListWidget()
        scenario_list.itemSelectionChanged.connect(self._load_selected_scenario)
        self.scenario_list_widget = scenario_list
        navigation_dock.setWidget(scenario_list)
        self.addDockWidget(Qt.LeftDockWidgetArea, navigation_dock)
        self._refresh_scenario_list()

    def _build_summary_dock(self) -> None:
        summary_dock = QDockWidget("Live Summary", self)
        summary_dock.setAllowedAreas(Qt.RightDockWidgetArea)

        summary_widget = QWidget()
        layout = QVBoxLayout(summary_widget)
        layout.addWidget(QLabel("Critical Coverage"))
        self.summary_labels["critical"] = QLabel()
        layout.addWidget(self.summary_labels["critical"])
        layout.addWidget(QLabel("Overall Coverage"))
        self.summary_labels["overall"] = QLabel()
        layout.addWidget(self.summary_labels["overall"])
        layout.addWidget(QLabel("Estimated Cost"))
        self.summary_labels["cost"] = QLabel()
        layout.addWidget(self.summary_labels["cost"])
        layout.addWidget(QLabel("Confidence"))
        self.summary_labels["confidence"] = QLabel()
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
        self.compare_tab_index = tabs.addTab(self._build_compare_tab(), "Compare")
        self.workspace_tabs = tabs
        self.setCentralWidget(tabs)

    def _build_overview_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        form = QFormLayout()
        self.name_input = QLineEdit()
        self.location_input = QLineEdit()
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
                self.location_input,
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

        form.addRow("Scenario Name", self.name_input)
        form.addRow("Location", self.location_input)
        form.addRow("Hazard", self.hazard_combo)
        form.addRow("Severity Band", self.severity_input)
        form.addRow("Duration (days)", self.duration_input)
        form.addRow("Infrastructure Damage %", self.infrastructure_damage_input)
        form.addRow("Total Population", self.total_population_input)
        form.addRow("Displaced Population", self.displaced_population_input)
        form.addRow("Children Under 5", self.children_input)
        form.addRow("Older Adults", self.older_adults_input)
        form.addRow("Pregnant/Lactating", self.pregnant_input)
        form.addRow("Medically Vulnerable", self.medically_vulnerable_input)
        form.addRow("Road Access Score", self.road_access_input)
        form.addRow("Health Facility Operability", self.health_operability_input)
        form.addRow("Local Water Liters/Day", self.water_availability_input)
        form.addRow("Local Food Supply Ratio", self.food_supply_ratio_input)
        form.addRow("Notes", self.notes_input)

        self.resource_table = QTableWidget(0, 5, self)
        self.resource_table.setHorizontalHeaderLabels(
            ["Name", "Category", "Quantity", "Unit", "Priority"]
        )
        self.resource_table.horizontalHeader().setStretchLastSection(True)
        resource_controls, self.resource_add_button, self.resource_remove_button = self._build_table_controls(
            on_add=self._add_resource_row,
            on_remove=lambda: self._remove_selected_rows(self.resource_table),
        )

        self.personnel_table = QTableWidget(0, 5, self)
        self.personnel_table.setHorizontalHeaderLabels(
            ["Role", "Count", "Shift Hours", "Hourly Cost", "Volunteers"]
        )
        self.personnel_table.horizontalHeader().setStretchLastSection(True)
        personnel_controls, self.personnel_add_button, self.personnel_remove_button = self._build_table_controls(
            on_add=self._add_personnel_row,
            on_remove=lambda: self._remove_selected_rows(self.personnel_table),
        )

        self.transport_table = QTableWidget(0, 6, self)
        self.transport_table.setHorizontalHeaderLabels(
            ["Asset", "Capacity (kg)", "Quantity", "Speed (km/h)", "Reliability", "Cost/km"]
        )
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
        button_layout.addWidget(save_button)
        button_layout.addWidget(analyze_button)

        layout.addLayout(form)
        layout.addWidget(QLabel("Resources"))
        layout.addWidget(self.resource_table)
        layout.addLayout(resource_controls)
        layout.addWidget(QLabel("Personnel"))
        layout.addWidget(self.personnel_table)
        layout.addLayout(personnel_controls)
        layout.addWidget(QLabel("Transportation"))
        layout.addWidget(self.transport_table)
        layout.addLayout(transport_controls)
        layout.addWidget(button_row)
        self._populate_editor_from_scenario(self.active_scenario)
        return widget

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

        layout.addWidget(table)
        return widget

    def _build_results_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        notes = QTextEdit()
        notes.setReadOnly(True)
        self.results_notes = notes
        self._update_results_view(self.initial_analysis)
        layout.addWidget(notes)
        return widget

    def _build_compare_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        selector_row = QHBoxLayout()
        self.compare_left_combo = QComboBox()
        self.compare_right_combo = QComboBox()
        self.compare_left_combo.currentIndexChanged.connect(self._run_comparison)
        self.compare_right_combo.currentIndexChanged.connect(self._run_comparison)
        run_compare_button = QPushButton("Run Comparison")
        run_compare_button.clicked.connect(self._run_comparison)
        swap_button = QPushButton("Swap")
        swap_button.clicked.connect(self._swap_comparison_selection)

        selector_row.addWidget(QLabel("Scenario A"))
        selector_row.addWidget(self.compare_left_combo)
        selector_row.addWidget(QLabel("Scenario B"))
        selector_row.addWidget(self.compare_right_combo)
        selector_row.addWidget(swap_button)
        selector_row.addWidget(run_compare_button)

        output = QTextEdit()
        output.setReadOnly(True)
        output.setPlainText("Select two scenarios and run comparison to view analysis deltas.")
        self.compare_output = output

        layout.addLayout(selector_row)
        layout.addWidget(output)
        return widget

    def _refresh_scenario_list(self, selected_scenario_id: str | None = None) -> None:
        if self.scenario_list_widget is None:
            return

        self.scenario_list_widget.blockSignals(True)
        self.scenario_list_widget.clear()
        summaries = self.scenario_repository.list_scenarios()
        for summary in summaries:
            variant_text = f"[{summary.variant_label}]"
            label = f"{summary.name} {variant_text} • {summary.hazard_type.value} • {summary.location_label}"
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, summary.scenario_id)
            self.scenario_list_widget.addItem(item)
            if selected_scenario_id and summary.scenario_id == selected_scenario_id:
                item.setSelected(True)

        if not selected_scenario_id and summaries:
            self.scenario_list_widget.setCurrentRow(0)
        self.scenario_list_widget.blockSignals(False)
        self._refresh_compare_selectors(summaries)

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
        self.location_input.setText(scenario.hazard_profile.location_label)
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
            hazard_profile=HazardProfile(
                hazard_type=hazard_type,
                severity_band=self.severity_input.text().strip() or "moderate",
                duration_days=self.duration_input.value(),
                location_label=self.location_input.text().strip() or "Unassigned Region",
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
        if self._is_locked_baseline(self.active_scenario):
            QMessageBox.warning(
                self,
                "Baseline Locked",
                "This baseline is locked. Branch a variant to make changes.",
            )
            return

        scenario = self._build_scenario_from_editor()
        if scenario.population_profile.displaced_population > scenario.population_profile.total_population:
            QMessageBox.warning(
                self,
                "Invalid Population",
                "Displaced population cannot exceed total affected population.",
            )
            return

        self.active_scenario = self.scenario_repository.save_scenario(scenario)
        self._refresh_scenario_list(selected_scenario_id=self.active_scenario.scenario_id)
        self.statusBar().showMessage(f"Saved scenario: {self.active_scenario.name}")

    def _run_analysis(self) -> None:
        self.active_scenario = self._build_scenario_from_editor()
        self.initial_analysis = self.planning_engine.analyze(self.active_scenario)
        self._update_summary_panel(self.initial_analysis)
        self._update_results_view(self.initial_analysis)
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
        self._update_summary_panel(self.initial_analysis)
        self._update_results_view(self.initial_analysis)
        self.statusBar().showMessage(f"Loaded scenario: {self.active_scenario.name}")

    def _open_compare_tab(self) -> None:
        if self.workspace_tabs is None or self.compare_tab_index is None:
            return
        self.workspace_tabs.setCurrentIndex(self.compare_tab_index)

    def _run_comparison(self) -> None:
        if self.compare_left_combo is None or self.compare_right_combo is None or self.compare_output is None:
            return

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

        left_lineage = self.scenario_repository.get_lineage(left_scenario.scenario_id)
        right_lineage = self.scenario_repository.get_lineage(right_scenario.scenario_id)

        lines = [
            f"Scenario A: {left_scenario.name} [{left_scenario.variant_label}]",
            f"Scenario B: {right_scenario.name} [{right_scenario.variant_label}]",
            f"Lineage A: {self._format_lineage(left_lineage)}",
            f"Lineage B: {self._format_lineage(right_lineage)}",
            "",
            "Top-level deltas (B - A):",
            f"- Critical coverage: {right_analysis.critical_coverage_percent - left_analysis.critical_coverage_percent:+.1f}%",
            f"- Overall coverage: {right_analysis.overall_coverage_percent - left_analysis.overall_coverage_percent:+.1f}%",
            f"- Total estimated cost: ${right_analysis.total_estimated_cost - left_analysis.total_estimated_cost:+,.2f}",
            "",
            f"Comparison call: {self._comparison_winner(left_analysis, right_analysis)}",
            "",
            "Detailed metric deltas:",
        ]

        shared_keys = sorted(set(left_analysis.metadata).intersection(right_analysis.metadata))
        for key in shared_keys:
            left_value = left_analysis.metadata[key]
            right_value = right_analysis.metadata[key]
            if isinstance(left_value, (int, float)) and isinstance(right_value, (int, float)):
                lines.append(f"- {key}: {right_value - left_value:+.2f}")

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

        self.compare_output.setPlainText("\n".join(lines))

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

    def _comparison_winner(self, left: AnalysisSummary, right: AnalysisSummary) -> str:
        left_score = (left.critical_coverage_percent * 2.0) + left.overall_coverage_percent - (left.total_estimated_cost / 10000)
        right_score = (right.critical_coverage_percent * 2.0) + right.overall_coverage_percent - (right.total_estimated_cost / 10000)
        if abs(left_score - right_score) < 0.01:
            return "Equivalent planning score across selected metrics."
        return "Scenario B leads selected metrics." if right_score > left_score else "Scenario A leads selected metrics."

    def _is_locked_baseline(self, scenario: Scenario) -> bool:
        return (
            scenario.variant_label == "baseline"
            and scenario.base_scenario_id is None
            and scenario.status == ScenarioStatus.LOCKED
        )

    def _apply_editor_lock_state(self) -> None:
        enabled = not self._is_locked_baseline(self.active_scenario)
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
            f"Critical coverage: {analysis.critical_coverage_percent}%",
            f"Overall coverage: {analysis.overall_coverage_percent}%",
            f"Estimated total cost: ${analysis.total_estimated_cost:,.2f}",
            f"Confidence: {analysis.confidence_level.value}",
            "",
            "Computed metrics:",
        ]
        for key, value in analysis.metadata.items():
            lines.append(f"- {key}: {value}")
        lines.append("")
        lines.append("Unmet critical needs:")
        if analysis.unmet_critical_needs:
            lines.extend(f"- {item}" for item in analysis.unmet_critical_needs)
        else:
            lines.append("- None")
        lines.append("")
        lines.append("Assumptions trace:")
        lines.extend(f"- {identifier}" for identifier in analysis.assumptions_trace)
        self.results_notes.setPlainText("\n".join(lines))