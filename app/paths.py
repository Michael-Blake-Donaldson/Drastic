from __future__ import annotations

import os
from pathlib import Path


APP_DIR_NAME = "Drastic"


def resolve_app_data_directory() -> Path:
    appdata = os.getenv("APPDATA")
    if appdata:
        return Path(appdata) / APP_DIR_NAME

    return Path.home() / f".{APP_DIR_NAME.lower()}"


def ensure_application_directories() -> dict[str, Path]:
    root = resolve_app_data_directory()
    directories = {
        "root": root,
        "exports": root / "exports",
        "logs": root / "logs",
        "backups": root / "backups",
    }

    for path in directories.values():
        path.mkdir(parents=True, exist_ok=True)

    return directories