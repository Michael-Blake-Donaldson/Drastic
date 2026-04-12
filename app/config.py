from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppConfig:
    app_name: str
    organization_name: str
    database_path: Path
    export_directory: Path
    log_directory: Path
    default_currency: str = "USD"
    default_unit_system: str = "metric"
    offline_mode: bool = True