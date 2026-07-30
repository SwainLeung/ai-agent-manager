"""Prompt template registry: version-controlled prompt storage."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class PromptTemplate:
    prompt_id: str
    content: str
    version: str
    tags: list[str]
    lifecycle: str = "active"
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class PromptRegistry:
    """Version-controlled prompt template storage."""

    def __init__(self, templates: list[PromptTemplate] | None = None):
        self.templates = list(templates or [])

    def add(self, prompt_id: str, content: str, version: str, tags: list[str] | None = None) -> PromptTemplate:
        existing = [t for t in self.templates if t.prompt_id == prompt_id and t.version == version]
        if existing:
            raise ValueError(f"prompt {prompt_id} version {version} already exists")
        now = _utc_now()
        template = PromptTemplate(
            prompt_id=prompt_id,
            content=content,
            version=version,
            tags=tags or [],
            lifecycle="active",
            created_at=now,
            updated_at=now,
        )
        self.templates.append(template)
        return template

    def get(self, prompt_id: str, version: str | None = None) -> PromptTemplate | None:
        matches = [t for t in self.templates if t.prompt_id == prompt_id and (version is None or t.version == version)]
        return matches[-1] if matches else None

    def list_by_tag(self, tag: str) -> list[PromptTemplate]:
        return [t for t in self.templates if tag in t.tags and t.lifecycle == "active"]

    def diff(self, prompt_id: str, v1: str, v2: str) -> str:
        t1 = self.get(prompt_id, v1)
        t2 = self.get(prompt_id, v2)
        if not t1 or not t2:
            raise ValueError(f"prompt {prompt_id} version {v1} or {v2} not found")
        lines1 = t1.content.splitlines(keepends=True)
        lines2 = t2.content.splitlines(keepends=True)
        result = [f"--- {prompt_id} v{v1}", f"+++ {prompt_id} v{v2}"]
        import difflib
        for line in difflib.unified_diff(lines1, lines2, fromfile=f"v{v1}", tofile=f"v{v2}"):
            result.append(line.rstrip("\n"))
        return "\n".join(result)

    def save(self, path: str | Path) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        payload = [t.to_dict() for t in self.templates]
        Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "PromptRegistry":
        source = Path(path)
        if not source.exists():
            return cls()
        payload = json.loads(source.read_text(encoding="utf-8"))
        return cls([PromptTemplate(**item) for item in payload])
