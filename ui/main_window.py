from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QDockWidget,
    QLabel,
    QListWidget,
    QMainWindow,
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
from domain.models import AnalysisSummary, AssumptionRecord, Scenario


class MainWindow(QMainWindow):
    def __init__(
        self,
        config: AppConfig,
        assumption_registry: tuple[AssumptionRecord, ...],
        active_scenario: Scenario,
        initial_analysis: AnalysisSummary,
    ) -> None:
        super().__init__()
        self.config = config
        self.assumption_registry = assumption_registry
        self.active_scenario = active_scenario
        self.initial_analysis = initial_analysis

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

        new_project_action = QAction("New Project", self)
        new_project_action.setStatusTip("Create a new scenario planning project")
        toolbar.addAction(new_project_action)

        compare_action = QAction("Compare Variants", self)
        compare_action.setStatusTip("Open the scenario comparison workspace")
        toolbar.addAction(compare_action)

        export_action = QAction("Export", self)
        export_action.setStatusTip("Export the active scenario package")
        toolbar.addAction(export_action)

    def _build_left_navigation(self) -> None:
        navigation_dock = QDockWidget("Workspace", self)
        navigation_dock.setAllowedAreas(Qt.LeftDockWidgetArea)

        navigation_list = QListWidget()
        navigation_list.addItems(
            [
                "Projects",
                "Scenarios",
                "Variants",
                "Templates",
                "Exports",
                "Settings",
            ]
        )
        navigation_dock.setWidget(navigation_list)
        self.addDockWidget(Qt.LeftDockWidgetArea, navigation_dock)

    def _build_summary_dock(self) -> None:
        summary_dock = QDockWidget("Live Summary", self)
        summary_dock.setAllowedAreas(Qt.RightDockWidgetArea)

        summary_widget = QWidget()
        layout = QVBoxLayout(summary_widget)
        layout.addWidget(QLabel("Critical Coverage"))
        layout.addWidget(QLabel(f"{self.initial_analysis.critical_coverage_percent}%"))
        layout.addWidget(QLabel("Overall Coverage"))
        layout.addWidget(QLabel(f"{self.initial_analysis.overall_coverage_percent}%"))
        layout.addWidget(QLabel("Estimated Cost"))
        layout.addWidget(QLabel(f"${self.initial_analysis.total_estimated_cost:,.2f}"))
        layout.addWidget(QLabel("Confidence"))
        layout.addWidget(QLabel(self.initial_analysis.confidence_level.value.title()))
        layout.addWidget(QLabel("Risk Flags"))
        if self.initial_analysis.risk_flags:
            for flag in self.initial_analysis.risk_flags:
                label = QLabel(f"• {flag.title}")
                label.setWordWrap(True)
                layout.addWidget(label)
        else:
            layout.addWidget(QLabel("No active risk flags"))
        layout.addStretch(1)

        summary_dock.setWidget(summary_widget)
        self.addDockWidget(Qt.RightDockWidgetArea, summary_dock)

    def _build_central_workspace(self) -> None:
        tabs = QTabWidget(self)
        tabs.addTab(self._build_overview_tab(), "Overview")
        tabs.addTab(self._build_assumptions_tab(), "Assumptions")
        tabs.addTab(self._build_results_tab(), "Results")
        self.setCentralWidget(tabs)

    def _build_overview_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        intro = QTextEdit()
        intro.setReadOnly(True)
        intro.setPlainText(
            "DRASTIC is being rebuilt as a Python-first, offline planning system.\n\n"
            f"Active seeded scenario: {self.active_scenario.name}\n"
            f"Hazard: {self.active_scenario.hazard_profile.hazard_type.value}\n"
            f"Duration: {self.active_scenario.hazard_profile.duration_days} days\n"
            f"Affected population: {self.active_scenario.population_profile.total_population:,}\n\n"
            "This foundation now includes a first-pass standards-backed analysis slice wired into the desktop shell."
        )

        layout.addWidget(intro)
        return widget

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
        lines = [
            f"Critical coverage: {self.initial_analysis.critical_coverage_percent}%",
            f"Overall coverage: {self.initial_analysis.overall_coverage_percent}%",
            f"Estimated total cost: ${self.initial_analysis.total_estimated_cost:,.2f}",
            f"Confidence: {self.initial_analysis.confidence_level.value}",
            "",
            "Computed metrics:",
        ]
        for key, value in self.initial_analysis.metadata.items():
            lines.append(f"- {key}: {value}")
        lines.append("")
        lines.append("Unmet critical needs:")
        if self.initial_analysis.unmet_critical_needs:
            lines.extend(f"- {item}" for item in self.initial_analysis.unmet_critical_needs)
        else:
            lines.append("- None")
        lines.append("")
        lines.append("Assumptions trace:")
        lines.extend(f"- {identifier}" for identifier in self.initial_analysis.assumptions_trace)
        notes.setPlainText("\n".join(lines))
        layout.addWidget(notes)
        return widget