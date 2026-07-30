from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Iterable


FRONTMATTER_DELIMITER = "---"
INDEX_NAMES = {"index.md", "readme.md", "wiki-index.md"}
DERIVED_EXTENSIONS = {".json", ".tsv", ".txt"}
OWNER_KEYS = ("owner", "maintainer", "responsible")
SOURCE_KEYS = ("source_id", "source", "source_url", "wikipedia_url", "wikidata_id")
SOURCE_FRESHNESS_KEYS = ("last_verified", "last_scraped", "scraped_at", "source_updated_at", "source_modified_at")
ARTIFACT_FRESHNESS_KEYS = ("generated_at", "created_at")
TIMESTAMP_KEYS = (*SOURCE_FRESHNESS_KEYS, *ARTIFACT_FRESHNESS_KEYS, "last_modified", "created")
WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]")
MARKDOWN_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
HEADING_RE = re.compile(r"^#{1,6}\s+(.+?)\s*$")


def _parse_frontmatter(raw: str) -> dict[str, Any]:
    lines = raw.splitlines()
    if not lines or lines[0].strip() != FRONTMATTER_DELIMITER:
        return {}
    result: dict[str, Any] = {}
    for line in lines[1:]:
        stripped = line.strip()
        if stripped == FRONTMATTER_DELIMITER:
            break
        if not stripped or stripped.startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        value = value.strip()
        if value.startswith("[") and value.endswith("]"):
            try:
                result[key.strip()] = json.loads(value)
                continue
            except json.JSONDecodeError:
                pass
        result[key.strip()] = value.strip("\"'")
    return result


def _read_text(path: Path) -> str:
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="replace")


def _parse_timestamp(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    if len(text) == 10:
        text = f"{text}T00:00:00+00:00"
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _metadata_value(metadata: dict[str, Any], keys: Iterable[str]) -> Any:
    for key in keys:
        if metadata.get(key):
            return metadata[key]
        nested = metadata.get("meta")
        if isinstance(nested, dict) and nested.get(key):
            return nested[key]
    return None


def _normalize_key(value: str) -> str:
    return re.sub(r"[^\w\u4e00-\u9fff]+", "", value.casefold())


def _title(path: Path, raw: str, metadata: dict[str, Any]) -> str:
    for key in ("title", "name"):
        if metadata.get(key):
            return str(metadata[key]).strip()
    for line in raw.splitlines():
        match = HEADING_RE.match(line.strip())
        if match:
            return match.group(1).strip()
    return path.stem.replace("_", " ").replace("-", " ").strip()


def _metadata(path: Path, raw: str) -> dict[str, Any]:
    if path.suffix.lower() in {".md", ".markdown"}:
        return _parse_frontmatter(raw)
    if path.suffix.lower() == ".json":
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            return {}
        return value if isinstance(value, dict) else {}
    return {}


def _classify(path: Path) -> str:
    if path.suffix.lower() in {".md", ".markdown"}:
        return "index" if path.name.casefold() in INDEX_NAMES else "source_entity"
    if path.suffix.lower() in DERIVED_EXTENSIONS:
        return "derived_artifact"
    return "other"


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _file_time(path: Path) -> datetime:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)


def _local_references(path: Path, raw: str) -> list[str]:
    if path.suffix.lower() not in {".md", ".markdown"}:
        return []
    values = [match.group(1).strip() for match in WIKILINK_RE.finditer(raw)]
    values.extend(match.group(1).split("#", 1)[0].strip() for match in MARKDOWN_LINK_RE.finditer(raw))
    return sorted({value for value in values if value and not re.match(r"^[a-z][a-z0-9+.-]*://", value, re.IGNORECASE)})


def _resolve_reference(source: Path, reference: str) -> Path:
    target = Path(reference)
    if target.suffix == "":
        target = target.with_suffix(".md")
    return (source.parent / target).resolve()


def _asset(root: Path, path: Path) -> dict[str, Any]:
    raw = _read_text(path)
    metadata = _metadata(path, raw)
    modified = _file_time(path)
    kind = _classify(path)
    source_freshness = _parse_timestamp(_metadata_value(metadata, SOURCE_FRESHNESS_KEYS))
    artifact_freshness = _parse_timestamp(_metadata_value(metadata, ARTIFACT_FRESHNESS_KEYS))
    freshness = source_freshness or artifact_freshness or (modified if kind != "source_entity" else None)
    title = _title(path, raw, metadata)
    return {
        "path": str(path),
        "relative_path": str(path.relative_to(root)).replace("\\", "/"),
        "kind": kind,
        "size": path.stat().st_size,
        "modified_at": _iso(modified),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "title": title,
        "normalized_key": _normalize_key(title),
        "owner": _metadata_value(metadata, OWNER_KEYS),
        "source": _metadata_value(metadata, SOURCE_KEYS),
        "freshness_at": _iso(freshness) if freshness else None,
        "source_freshness_at": _iso(source_freshness) if source_freshness else None,
        "metadata": {key: value for key, value in metadata.items() if key in {*OWNER_KEYS, *SOURCE_KEYS, *TIMESTAMP_KEYS, "title", "name", "version", "status"}},
        "references": _local_references(path, raw),
    }


def _finding(code: str, subject: str, severity: str, message: str, **extra: Any) -> dict[str, Any]:
    return {"code": code, "subject": subject, "severity": severity, "message": message, **extra}


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def run_local_audit(
    root: str | Path,
    output_dir: str | Path,
    *,
    stale_days: float = 2.0,
    now: datetime | None = None,
) -> dict[str, Any]:
    if stale_days < 0:
        raise ValueError("stale_days must be non-negative")
    root_path = Path(root).resolve()
    output_path = Path(output_dir).resolve()
    if not root_path.is_dir():
        raise ValueError(f"audit root is not a directory: {root_path}")
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    files = sorted((path for path in root_path.rglob("*") if path.is_file()), key=lambda item: str(item).casefold())
    assets = [_asset(root_path, path) for path in files]
    source_assets = [item for item in assets if item["kind"] == "source_entity"]
    latest_source_modified = max((_parse_timestamp(item["modified_at"]) for item in source_assets), default=None)
    cutoff = current - timedelta(days=stale_days)
    findings: list[dict[str, Any]] = []

    exact_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    key_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in assets:
        exact_groups[item["sha256"]].append(item)
        if item["kind"] == "source_entity" and item["normalized_key"]:
            key_groups[item["normalized_key"]].append(item)
        freshness = _parse_timestamp(item["freshness_at"])
        if freshness and freshness < cutoff:
            findings.append(_finding("stale", item["relative_path"], "warning", "asset freshness is older than the configured threshold", freshness_at=item["freshness_at"], cutoff=_iso(cutoff)))
        elif item["kind"] == "source_entity" and not item["source_freshness_at"]:
            findings.append(_finding("freshness-unknown", item["relative_path"], "warning", "source entity has no source verification or scrape timestamp"))
        if item["kind"] == "derived_artifact" and latest_source_modified and _parse_timestamp(item["modified_at"]) < latest_source_modified:
            findings.append(_finding("derived-drift", item["relative_path"], "warning", "derived artifact is older than the newest source entity", newest_source_modified=_iso(latest_source_modified)))
        if not item["owner"]:
            findings.append(_finding("unowned", item["relative_path"], "warning", "asset has no explicit owner or maintainer"))

    for digest, group in exact_groups.items():
        if len(group) > 1:
            findings.append(_finding("exact-duplicate", digest, "warning", "assets have identical SHA-256 content", assets=[item["relative_path"] for item in group]))
    for key, group in key_groups.items():
        if len(group) > 1:
            findings.append(_finding("normalized-duplicate", key, "warning", "source entities share the same normalized title key", assets=[item["relative_path"] for item in group]))

    known_paths = {path.resolve() for path in files}
    incoming: dict[Path, int] = defaultdict(int)
    for item in assets:
        source = root_path / item["relative_path"]
        for reference in item["references"]:
            target = _resolve_reference(source, reference)
            if target not in known_paths:
                findings.append(_finding("unresolved-reference", item["relative_path"], "warning", "local reference does not resolve to a scanned file", reference=reference))
            else:
                incoming[target] += 1
    for item in source_assets:
        if incoming[root_path / item["relative_path"]] == 0:
            findings.append(_finding("orphan-source", item["relative_path"], "warning", "source entity has no incoming local reference"))

    merge_candidates: list[dict[str, Any]] = []
    for digest, group in exact_groups.items():
        if len(group) > 1:
            merge_candidates.append({"type": "exact_duplicate", "key": digest, "assets": [item["relative_path"] for item in group], "recommended_action": "human_review"})
    for key, group in key_groups.items():
        if len(group) > 1:
            merge_candidates.append({"type": "normalized_duplicate", "key": key, "assets": [item["relative_path"] for item in group], "recommended_action": "human_review"})

    delete_candidates = [
        {
            "path": item["relative_path"],
            "recommended_action": "quarantine_after_review" if item["kind"] == "derived_artifact" else "human_review",
            "reasons": sorted({finding["code"] for finding in findings if finding["subject"] == item["relative_path"]}),
        }
        for item in assets
        if any(finding["subject"] == item["relative_path"] and finding["code"] in {"stale", "derived-drift", "exact-duplicate", "normalized-duplicate"} for finding in findings)
    ]
    summary = {
        "asset_count": len(assets),
        "source_entity_count": len(source_assets),
        "derived_artifact_count": sum(item["kind"] == "derived_artifact" for item in assets),
        "finding_count": len(findings),
        "finding_counts": {code: sum(item["code"] == code for item in findings) for code in sorted({item["code"] for item in findings})},
        "stale_days": stale_days,
        "scanned_at": _iso(current),
    }
    manifest = {"schema_version": 1, "root": str(root_path), "summary": summary, "assets": assets}
    report = {"schema_version": 1, "root": str(root_path), "summary": summary, "findings": findings}
    merge_payload = {"schema_version": 1, "root": str(root_path), "candidates": merge_candidates}
    delete_payload = {"schema_version": 1, "root": str(root_path), "candidates": delete_candidates, "mutation_performed": False}
    _write_json(output_path / "flowus-local-manifest.json", manifest)
    _write_json(output_path / "flowus-anti-entropy-report.json", report)
    _write_json(output_path / "flowus-merge-candidates.json", merge_payload)
    _write_json(output_path / "flowus-delete-candidates.json", delete_payload)
    return {"root": str(root_path), "output_dir": str(output_path), "summary": summary, "findings": findings, "merge_candidates": merge_candidates, "delete_candidates": delete_candidates, "mutation_performed": False}
