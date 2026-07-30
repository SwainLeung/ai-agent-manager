"""Canary / gradual rollout for skill lifecycle transitions."""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class CanaryConfig:
    skill_id: str
    new_version: str
    traffic_percentage: int = 10  # 0-100, percent of traffic to new version
    cooldown_hours: float = 24.0
    min_success_rate: float = 0.85
    status: str = "running"  # running | promoted | rolled_back

    def to_dict(self) -> dict[str, Any]:
        return {
            "skill_id": self.skill_id,
            "new_version": self.new_version,
            "traffic_percentage": self.traffic_percentage,
            "cooldown_hours": self.cooldown_hours,
            "min_success_rate": self.min_success_rate,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "CanaryConfig":
        return cls(
            skill_id=str(d["skill_id"]),
            new_version=str(d["new_version"]),
            traffic_percentage=int(d.get("traffic_percentage", 10)),
            cooldown_hours=float(d.get("cooldown_hours", 24)),
            min_success_rate=float(d.get("min_success_rate", 0.85)),
            status=str(d.get("status", "running")),
        )


class CanaryStore:
    """Persistent canary rollout configuration store."""

    def __init__(self, configs: list[CanaryConfig] | None = None):
        self._configs = list(configs or [])

    @property
    def active(self) -> list[CanaryConfig]:
        return [c for c in self._configs if c.status == "running"]

    def add(self, config: CanaryConfig) -> None:
        existing = [c for c in self._configs if c.skill_id == config.skill_id and c.status == "running"]
        if existing:
            raise ValueError(f"canary already running for: {config.skill_id}")
        self._configs.append(config)

    def should_route_new(self, skill_id: str) -> bool:
        """Return True if this request should use the new version."""
        for config in self.active:
            if config.skill_id == skill_id:
                return random.randint(1, 100) <= config.traffic_percentage
        return False

    def promote(self, skill_id: str) -> CanaryConfig | None:
        for config in self._configs:
            if config.skill_id == skill_id and config.status == "running":
                config.status = "promoted"
                return config
        return None

    def rollback(self, skill_id: str) -> CanaryConfig | None:
        for config in self._configs:
            if config.skill_id == skill_id and config.status == "running":
                config.status = "rolled_back"
                return config
        return None

    def save(self, path: str | Path) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        data = [c.to_dict() for c in self._configs]
        Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "CanaryStore":
        source = Path(path)
        if not source.exists():
            return cls()
        data = json.loads(source.read_text(encoding="utf-8"))
        return cls([CanaryConfig.from_dict(item) for item in data])
