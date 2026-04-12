from __future__ import annotations

from datetime import datetime
from pathlib import Path


def write_text_report(export_directory: Path, prefix: str, content: str) -> Path:
    export_directory.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_prefix = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in prefix).strip("_")
    safe_prefix = safe_prefix or "report"
    destination = export_directory / f"{safe_prefix}_{timestamp}.txt"
    destination.write_text(content, encoding="utf-8")
    return destination