"""Configurable health checks for data sources (filesystem paths, URLs)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.request import urlopen, Request
from urllib.error import URLError
import json


@dataclass
class HealthCheckResult:
    check_id: str
    status: str  # "ok" | "warning" | "fail"
    message: str
    detail: dict[str, Any] | None = None


def run_health_check(config: dict[str, Any]) -> HealthCheckResult:
    """Run a single health check based on config dict.

    Config keys:
        id (str): unique check ID
        type (str): "file" or "url"
        path (str): file path or URL
        max_age_hours (float, optional): max file age in hours
        expected_size_min (int, optional): minimum file size in bytes
        timeout_seconds (float, optional): URL timeout
    """
    cid = config.get("id", "unknown")
    check_type = str(config.get("type", "file"))
    path = str(config.get("path", ""))
    max_age = float(config.get("max_age_hours", 0))
    min_size = int(config.get("expected_size_min", 0))

    if check_type == "file":
        p = Path(path)
        if not p.exists():
            return HealthCheckResult(cid, "fail", f"file not found: {path}")
        if not p.is_file():
            return HealthCheckResult(cid, "fail", f"path is not a file: {path}")
        stat = p.stat()
        issues = []
        if min_size and stat.st_size < min_size:
            issues.append(f"size {stat.st_size} < {min_size}")
        if max_age:
            age_h = (datetime.now(timezone.utc).timestamp() - stat.st_mtime) / 3600
            if age_h > max_age:
                issues.append(f"age {age_h:.1f}h > {max_age}h")
        detail = {"size": stat.st_size, "modified": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()}
        if issues:
            return HealthCheckResult(cid, "warning", "; ".join(issues), detail)
        return HealthCheckResult(cid, "ok", "file is accessible", detail)

    elif check_type == "url":
        timeout = float(config.get("timeout_seconds", 10))
        try:
            req = Request(path, method="HEAD")
            resp = urlopen(req, timeout=timeout)
            detail = {"status_code": resp.status, "content_type": resp.headers.get("Content-Type", "")}
            if resp.status >= 400:
                return HealthCheckResult(cid, "fail", f"HTTP {resp.status}", detail)
            return HealthCheckResult(cid, "ok", f"HTTP {resp.status}", detail)
        except (URLError, TimeoutError, OSError) as exc:
            return HealthCheckResult(cid, "fail", f"unreachable: {exc}")

    return HealthCheckResult(cid, "fail", f"unsupported check type: {check_type}")


def run_health_checks(configs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Run multiple health checks and return summary list."""
    results = []
    for config in configs:
        result = run_health_check(config)
        results.append({
            "check_id": result.check_id,
            "status": result.status,
            "message": result.message,
            "detail": result.detail,
        })
    return results
