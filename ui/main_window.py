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
from domain.models import AssumptionRecord


class MainWindow(QMainWindow):
    def __init__(self, config: AppConfig, assumption_registry: tuple[AssumptionRecord, ...]) -> None:
        super().__init__()
        self.config = config
        self.assumption_registry = assumption_registry

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
        layout.addWidget(QLabel("Pending engine implementation"))
        layout.addWidget(QLabel("Overall Coverage"))
        layout.addWidget(QLabel("Pending engine implementation"))
        layout.addWidget(QLabel("Risk Flags"))
        layout.addWidget(QLabel("No active scenario loaded"))
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
            "This initial foundation establishes the desktop shell, persistence layer, and assumption registry so the planning engine can be implemented against stable contracts."
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
        notes.setPlainText(
            "Result contracts will be connected here once the first calculation modules are implemented.\n\n"
            "Planned result blocks:\n"
            "- Critical and overall coverage\n"
            "- Unmet critical needs\n"
            "- Staffing shortfalls by role\n"
            "- Transport bottlenecks and delivery waves\n"
            "- Cost bundle and confidence trace\n"
            "- Scenario comparison deltas"
        )
        layout.addWidget(notes)
        return widget