"""Temp file garbage collector: scan and report cleanup candidates."""

from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
from typing import Any


SAFELIST = {".git", ".agent-manager", "config", "src", "tests", "docs", "examples", "scripts", "theory txt"}


def scan_cleanup_candidates(root_dir: str | Path, *, max_age_hours: float = 24, dry_run: bool = True) -> dict[str, Any]:
    """Scan for temp/artifact files older than max_age_hours.

    Parameters
    ----------
    root_dir : str | Path
        Root directory to scan.
    max_age_hours : float
        Files older than this are candidates.
    dry_run : bool
        When True, only report; no deletion.

    Returns
    -------
    dict with: candidates (list), total_size_bytes, file_count, dry_run
    """
    root = Path(root_dir)
    candidates = []
    now = datetime.now(timezone.utc).timestamp()
    for entry in root.rglob("*"):
        if not entry.is_file():
            continue
        # Skip safelisted directories
        rel = entry.relative_to(root)
        parts = rel.parts
        if any(p in SAFELIST for p in parts):
            continue
        # Skip common build/cache artifacts
        skip_extensions = {".pyc", ".pyo", ".log", ".tmp", ".bak", ".swp"}
        if entry.suffix in skip_extensions:
            age_h = (now - entry.stat().st_mtime) / 3600
            if age_h > max_age_hours:
                candidates.append({
                    "path": str(rel),
                    "size": entry.stat().st_size,
                    "age_hours": round(age_h, 1),
                    "extension": entry.suffix,
                })
                continue
        # Skip __pycache__ directories
        if "__pycache__" in parts:
            age_h = (now - entry.stat().st_mtime) / 3600
            if age_h > max_age_hours:
                candidates.append({
                    "path": str(rel),
                    "size": entry.stat().st_size,
                    "age_hours": round(age_h, 1),
                    "extension": entry.suffix,
                    "note": "in __pycache__",
                })
    total_size = sum(c["size"] for c in candidates)
    return {
        "candidates": sorted(candidates, key=lambda x: x["age_hours"], reverse=True),
        "total_size_bytes": total_size,
        "file_count": len(candidates),
        "dry_run": dry_run,
    }
