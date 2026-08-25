"""Pydantic contract for dbt_arch.yaml and its loader."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, model_validator

from dbt_arch_unit.violation import Severity

CONFIG_FILENAME = "dbt_arch.yaml"

# Keys handled by RuleConfig itself; anything else on a rule entry is rule-specific
# config and gets folded into `config`.
_RESERVED_RULE_KEYS = frozenset(
    {
        "name",
        "severity",
        "include",
        "exclude",
        "scope",
        "ignore",
        "tags",
        "resource_types",
        "config",
    }
)


class ConfigError(Exception):
    """Raised when the config file is missing or invalid."""


class ProjectSettings(BaseModel):
    dir: str = "."
    manifest: str = "target/manifest.json"
    models_path: str = "models"
    # Any model whose path isn't matched by an explicit `layers:` entry takes its
    # layer name from its top-level folder under models_path. Set false to only
    # recognise explicitly-declared layers.
    auto_layers: bool = True


class LayerDef(BaseModel):
    paths: list[str] = Field(default_factory=list)
    prefixes: list[str] = Field(default_factory=list)


class Defaults(BaseModel):
    severity: Severity = Severity.ERROR
    include: list[str] = Field(default_factory=lambda: ["models/**"])
    exclude: list[str] = Field(default_factory=list)


class RuleConfig(BaseModel):
    """One entry in the `rules:` list."""

    name: str
    severity: Severity | None = None
    include: list[str] | None = None  # path globs
    exclude: list[str] | None = None  # path globs
    scope: list[str] | None = None  # run only on these layers
    ignore: list[str] | None = None  # run on every layer except these
    tags: list[str] | None = None
    resource_types: list[str] | None = None
    config: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _fold_inline_config(cls, data: Any) -> Any:
        """Allow rule params as inline YAML keys, not just under `config:`.

        `- name: max-lines-of-code` / `max: 200` is equivalent to the older
        `config: { max: 200 }`. Inline keys win if both are present.
        """
        if not isinstance(data, dict):
            return data
        inline = {k: v for k, v in data.items() if k not in _RESERVED_RULE_KEYS}
        if not inline:
            return data
        rest = {k: v for k, v in data.items() if k in _RESERVED_RULE_KEYS}
        rest["config"] = {**(data.get("config") or {}), **inline}
        return rest


class ArchUnitConfig(BaseModel):
    version: int = 1
    project: ProjectSettings = Field(default_factory=ProjectSettings)
    layers: dict[str, LayerDef] = Field(default_factory=dict)
    defaults: Defaults = Field(default_factory=Defaults)
    rules: list[RuleConfig] = Field(default_factory=list)

    def effective_severity(self, rule: RuleConfig) -> Severity:
        return rule.severity or self.defaults.severity

    def effective_include(self, rule: RuleConfig) -> list[str]:
        return rule.include if rule.include is not None else self.defaults.include

    def effective_exclude(self, rule: RuleConfig) -> list[str]:
        extra = rule.exclude or []
        return [*self.defaults.exclude, *extra]


def find_config(start: Path) -> Path | None:
    """Search `start` and its parents for dbt_arch.yaml."""
    start = start.resolve()
    for directory in [start, *start.parents]:
        candidate = directory / CONFIG_FILENAME
        if candidate.exists():
            return candidate
    return None


def load_config(path: Path) -> ArchUnitConfig:
    if not path.exists():
        raise ConfigError(f"config not found at '{path}'")
    data = yaml.safe_load(path.read_text()) or {}
    try:
        return ArchUnitConfig.model_validate(data)
    except Exception as exc:  # pydantic ValidationError -> friendly message
        raise ConfigError(f"invalid {CONFIG_FILENAME}: {exc}") from exc
