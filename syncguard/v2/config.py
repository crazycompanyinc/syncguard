"""Configuration drift across environments."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class ConfigurationDrift:
    key: str
    environments: dict[str, Any]
    severity: str
    message: str


class ConfigurationDriftTracker:
    """Compare environment configuration maps."""

    def compare(self, configs: dict[str, dict[str, Any]], protected_keys: set[str] | None = None) -> list[ConfigurationDrift]:
        protected = protected_keys or set()
        keys = sorted({key for config in configs.values() for key in config})
        drifts: list[ConfigurationDrift] = []
        for key in keys:
            values = {env: config.get(key) for env, config in sorted(configs.items())}
            if len(set(values.values())) > 1:
                severity = "high" if key in protected or "production" in values else "medium"
                drifts.append(ConfigurationDrift(key, values, severity, f"`{key}` differs across environments"))
        return drifts
