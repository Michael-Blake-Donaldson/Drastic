from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


def _normalize_detail_value(value: Any) -> Any:
    if isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return value[:256]
    if isinstance(value, (list, tuple)):
        normalized = [_normalize_detail_value(item) for item in value]
        return normalized[:32]
    if isinstance(value, dict):
        normalized_dict: dict[str, Any] = {}
        for index, (key, child) in enumerate(value.items()):
            if index >= 32:
                break
            normalized_dict[str(key)[:128]] = _normalize_detail_value(child)
        return normalized_dict
    return str(value)[:256]


def append_performance_event(
    log_directory: Path,
    event_name: str,
    duration_ms: float,
    details: Mapping[str, Any] | None = None,
) -> Path:
    """Append a structured performance event as NDJSON.

    This logger intentionally stores only bounded, low-sensitivity values and
    avoids persisting full free-form user inputs.
    """
    log_directory.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "event": event_name,
        "duration_ms": round(float(duration_ms), 3),
    }
    if details:
        payload["details"] = {
            str(key)[:128]: _normalize_detail_value(value)
            for key, value in list(details.items())[:32]
        }

    output_path = log_directory / "performance.ndjson"
    with output_path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(payload, separators=(",", ":"), ensure_ascii=True))
        stream.write("\n")

    return output_path
