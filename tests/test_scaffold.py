from __future__ import annotations

from pathlib import Path

import yaml

from dbt_arch_unit.config import ArchUnitConfig
from dbt_arch_unit.rules import all_rules
from dbt_arch_unit.scaffold import inspect_dbt_project, render_config

FIXTURE = Path(__file__).parent / "fixtures" / "demo_project"


def test_inspect_valid_project():
    ins = inspect_dbt_project(FIXTURE)
    assert ins.is_dbt_project is True
    assert ins.model_paths == ["models"]
    assert set(ins.detected_layers) == {"staging", "marts", "reporting"}
    assert ins.detected_layers["marts"] == ["fct_", "dim_"]


def test_inspect_empty_dir(tmp_path):
    ins = inspect_dbt_project(tmp_path)
    assert ins.is_dbt_project is False
    # the required dbt_project.yml check must have failed
    assert any(c.name == "dbt_project.yml present" and not c.ok for c in ins.checks)


def test_inspect_missing_models_dir(tmp_path):
    (tmp_path / "dbt_project.yml").write_text("name: demo\nprofile: demo\n")
    ins = inspect_dbt_project(tmp_path)
    assert ins.is_dbt_project is False
    assert any(c.name == "models directory exists" and not c.ok for c in ins.checks)


def test_render_config_is_valid_yaml():
    text = render_config("models", {"staging": ["stg_"], "marts": ["fct_", "dim_"]})
    cfg = ArchUnitConfig.model_validate(yaml.safe_load(text))
    assert cfg.version == 1  # default — not emitted
    assert cfg.layers["marts"].prefixes == ["fct_", "dim_"]
    assert any(r.name == "expect-dependencies" for r in cfg.rules)
    # redundant defaults are omitted for a standard 'models' path
    assert "version:" not in text
    assert "defaults:" not in text


def test_render_config_enables_a_few_and_comments_the_rest():
    text = render_config("models", {"staging": ["stg_"], "marts": ["fct_", "dim_"]})
    parsed = yaml.safe_load(text)
    active = {r["name"] for r in parsed["rules"]}
    # a small, high-signal active set — not everything
    assert "expect-dependencies" in active
    assert 3 <= len(active) <= 10
    # every registered rule appears somewhere in the file (active or commented catalog)
    for meta in all_rules():
        assert meta.name in text, f"{meta.name} missing from scaffold catalog"
    # the non-active ones are present but commented out
    inactive = {m.name for m in all_rules()} - active
    assert inactive, "expected some commented rules"
    for name in inactive:
        assert f"# - name: {name}" in text


def test_render_config_defaults_when_no_layers():
    parsed = yaml.safe_load(render_config("models", {}))
    assert set(parsed["layers"]) == {"staging", "intermediate", "marts", "reporting"}
