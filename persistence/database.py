from __future__ import annotations

import sqlite3
from pathlib import Path


class DatabaseManager:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path

    def initialize(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.database_path) as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS app_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS scenarios (
                    scenario_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    variant_label TEXT NOT NULL DEFAULT 'baseline',
                    base_scenario_id TEXT,
                    hazard_type TEXT NOT NULL,
                    severity_band TEXT NOT NULL,
                    duration_days INTEGER NOT NULL,
                    location_label TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scenario_id TEXT,
                    event_type TEXT NOT NULL,
                    event_timestamp TEXT NOT NULL,
                    detail TEXT NOT NULL
                )
                """
            )

            cursor.execute("PRAGMA table_info(scenarios)")
            existing_columns = {row[1] for row in cursor.fetchall()}
            if "variant_label" not in existing_columns:
                cursor.execute(
                    "ALTER TABLE scenarios ADD COLUMN variant_label TEXT NOT NULL DEFAULT 'baseline'"
                )
            if "base_scenario_id" not in existing_columns:
                cursor.execute("ALTER TABLE scenarios ADD COLUMN base_scenario_id TEXT")
            connection.commit()