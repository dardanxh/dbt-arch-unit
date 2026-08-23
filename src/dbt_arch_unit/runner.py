"""Orchestration: load artifacts, run configured rules, collect violations."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from dbt_arch_unit.config import ArchUnitConfig
from dbt_arch_unit.context import ProjectContext
from dbt_arch_unit.parsers.manifest_parser import load_manifest
from dbt_arch_unit.rules import _REGISTRY
from dbt_arch_unit.violation import Severity, Violation


@dataclass
class RunResult:
    violations: list[Violation] = field(default_factory=list)
    unknown_rules: list[str] = field(default_factory=list)

    @property
    def errors(self) -> list[Violation]:
        return [v for v in self.violations if v.severity is Severity.ERROR]

    @property
    def warnings(self) -> list[Violation]:
        return [v for v in self.violations if v.severity is Severity.WARNING]

    @property
    def has_errors(self) -> bool:
        return bool(self.errors)


def build_context(config: ArchUnitConfig) -> ProjectContext:
    project_dir = Path(config.project.dir).resolve()
    manifest_path = project_dir / config.project.manifest
    manifest = load_manifest(manifest_path)
    return ProjectContext(config, manifest)


def run(config: ArchUnitConfig, ctx: ProjectContext) -> RunResult:
    result = RunResult()
    for rule_cfg in config.rules:
        entry = _REGISTRY.get(rule_cfg.name)
        if entry is None:
            result.unknown_rules.append(rule_cfg.name)
            continue
        _, fn = entry
        try:
            result.violations.extend(fn(ctx, rule_cfg))
        except Exception as exc:  # keep the run resilient; surface as an error
            result.violations.append(
                Violation(
                    rule=rule_cfg.name,
                    severity=Severity.ERROR,
                    message=f"rule crashed: {exc}",
                    node="<internal>",
                )
            )
    return result
