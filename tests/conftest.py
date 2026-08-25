from __future__ import annotations

from pathlib import Path

import pytest

from dbt_arch_unit.config import RuleConfig, load_config
from dbt_arch_unit.context import ProjectContext
from dbt_arch_unit.parsers.manifest_parser import load_manifest
from dbt_arch_unit.rules import get_rule

FIXTURE = Path(__file__).parent / "fixtures" / "demo_project"


@pytest.fixture
def ctx() -> ProjectContext:
    config = load_config(FIXTURE / "dbt_arch.yaml")
    config.project.dir = str(FIXTURE)
    manifest = load_manifest(FIXTURE / "target" / "manifest.json")
    return ProjectContext(config, manifest)


@pytest.fixture
def run(ctx):
    def _run(name: str, **kwargs) -> set[str]:
        _, fn = get_rule(name)
        rule = RuleConfig(name=name, **kwargs)
        return {v.node for v in fn(ctx, rule)}

    return _run
