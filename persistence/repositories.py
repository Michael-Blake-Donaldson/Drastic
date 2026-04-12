from __future__ import annotations

import json
import sqlite3
from dataclasses import replace
from pathlib import Path

from domain.models import Scenario, ScenarioSummary, utc_now
from domain.serialization import scenario_from_dict, scenario_to_dict


class ScenarioRepository:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path

    def list_scenarios(self) -> list[ScenarioSummary]:
        with sqlite3.connect(self.database_path) as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT scenario_id, name, hazard_type, severity_band, location_label, status, updated_at
                FROM scenarios
                ORDER BY updated_at DESC
                """
            )
            rows = cursor.fetchall()

        return [
            ScenarioSummary(
                scenario_id=row[0],
                name=row[1],
                hazard_type=row[2],
                severity_band=row[3],
                location_label=row[4],
                status=row[5],
                updated_at=utc_now().fromisoformat(row[6]),
            )
            for row in rows
        ]

    def get_scenario(self, scenario_id: str) -> Scenario | None:
        with sqlite3.connect(self.database_path) as connection:
            cursor = connection.cursor()
            cursor.execute(
                "SELECT payload_json FROM scenarios WHERE scenario_id = ?",
                (scenario_id,),
            )
            row = cursor.fetchone()

        if row is None:
            return None

        payload = json.loads(row[0])
        return scenario_from_dict(payload)

    def save_scenario(self, scenario: Scenario) -> Scenario:
        updated_scenario = replace(scenario, updated_at=utc_now())
        payload_json = json.dumps(scenario_to_dict(updated_scenario), indent=2)
        with sqlite3.connect(self.database_path) as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                INSERT INTO scenarios (
                    scenario_id,
                    project_id,
                    name,
                    hazard_type,
                    severity_band,
                    duration_days,
                    location_label,
                    status,
                    created_at,
                    updated_at,
                    payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(scenario_id) DO UPDATE SET
                    name = excluded.name,
                    hazard_type = excluded.hazard_type,
                    severity_band = excluded.severity_band,
                    duration_days = excluded.duration_days,
                    location_label = excluded.location_label,
                    status = excluded.status,
                    updated_at = excluded.updated_at,
                    payload_json = excluded.payload_json
                """,
                (
                    updated_scenario.scenario_id,
                    updated_scenario.project_id,
                    updated_scenario.name,
                    updated_scenario.hazard_profile.hazard_type.value,
                    updated_scenario.hazard_profile.severity_band,
                    updated_scenario.hazard_profile.duration_days,
                    updated_scenario.hazard_profile.location_label,
                    updated_scenario.status.value,
                    updated_scenario.created_at.isoformat(),
                    updated_scenario.updated_at.isoformat(),
                    payload_json,
                ),
            )
            cursor.execute(
                """
                INSERT INTO audit_events (scenario_id, event_type, event_timestamp, detail)
                VALUES (?, ?, ?, ?)
                """,
                (
                    updated_scenario.scenario_id,
                    "scenario_saved",
                    updated_scenario.updated_at.isoformat(),
                    f"Scenario '{updated_scenario.name}' persisted to SQLite.",
                ),
            )
            connection.commit()

        return updated_scenario