from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from app.config import AppConfig
from app.paths import ensure_application_directories
from engine.planner import PlanningEngine
from persistence.database import DatabaseManager
from persistence.repositories import ScenarioRepository
from reference_data.assumptions import build_default_assumption_registry
from services.scenario_factory import build_seed_scenario
from ui.main_window import MainWindow


def build_app_config() -> AppConfig:
    directories = ensure_application_directories()
    return AppConfig(
        app_name="DRASTIC",
        organization_name="DRASTIC",
        database_path=directories["root"] / "drastic.db",
        export_directory=directories["exports"],
        log_directory=directories["logs"],
    )


def run_desktop_app() -> int:
    config = build_app_config()
    database_manager = DatabaseManager(config.database_path)
    database_manager.initialize()
    scenario_repository = ScenarioRepository(config.database_path)

    app = QApplication(sys.argv)
    app.setApplicationName(config.app_name)
    app.setOrganizationName(config.organization_name)

    assumption_registry = build_default_assumption_registry()
    planning_engine = PlanningEngine(assumption_registry)
    scenario_summaries = scenario_repository.list_scenarios()
    if scenario_summaries:
        active_scenario = scenario_repository.get_scenario(scenario_summaries[0].scenario_id)
    else:
        active_scenario = scenario_repository.save_scenario(build_seed_scenario())

    if active_scenario is None:
        active_scenario = scenario_repository.save_scenario(build_seed_scenario())

    initial_analysis = planning_engine.analyze(active_scenario)
    window = MainWindow(
        config=config,
        assumption_registry=assumption_registry,
        scenario_repository=scenario_repository,
        planning_engine=planning_engine,
        active_scenario=active_scenario,
        initial_analysis=initial_analysis,
    )
    window.show()
    return app.exec()