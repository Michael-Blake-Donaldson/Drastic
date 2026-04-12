from __future__ import annotations

import json
import sqlite3
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from domain.enums import HazardType, ScenarioStatus
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
                SELECT scenario_id, name, variant_label, base_scenario_id, hazard_type, severity_band, location_label, status, updated_at
                FROM scenarios
                ORDER BY updated_at DESC
                """
            )
            rows = cursor.fetchall()

        return [
            ScenarioSummary(
                scenario_id=row[0],
                name=row[1],
                variant_label=row[2],
                base_scenario_id=row[3],
                hazard_type=HazardType(row[4]),
                severity_band=row[5],
                location_label=row[6],
                status=ScenarioStatus(row[7]),
                updated_at=datetime.fromisoformat(row[8]),
            )
            for row in rows
        ]

    def branch_variant(self, source_scenario_id: str, variant_label: str) -> Scenario | None:
        source = self.get_scenario(source_scenario_id)
        if source is None:
            return None

        now = utc_now()
        variant = replace(
            source,
            scenario_id=uuid4().hex,
            name=f"{source.name} [{variant_label}]",
            variant_label=variant_label,
            base_scenario_id=source.scenario_id,
            created_at=now,
            updated_at=now,
        )
        return self.save_scenario(variant)

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
                    variant_label,
                    base_scenario_id,
                    hazard_type,
                    severity_band,
                    duration_days,
                    location_label,
                    status,
                    created_at,
                    updated_at,
                    payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(scenario_id) DO UPDATE SET
                    name = excluded.name,
                    variant_label = excluded.variant_label,
                    base_scenario_id = excluded.base_scenario_id,
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
                    updated_scenario.variant_label,
                    updated_scenario.base_scenario_id,
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