from __future__ import annotations

from pathlib import Path

from dbt_arch_unit.config import ArchUnitConfig, LayerDef, ProjectSettings, RuleConfig
from dbt_arch_unit.context import ProjectContext
from dbt_arch_unit.parsers.manifest_parser import load_manifest

FIXTURE = Path(__file__).parent / "fixtures" / "demo_project"


def _ctx(config: ArchUnitConfig) -> ProjectContext:
    config.project.dir = str(FIXTURE)
    manifest = load_manifest(FIXTURE / "target" / "manifest.json")
    return ProjectContext(config, manifest)


def test_auto_layers_on_by_default():
    # No config at all: every folder under models/ becomes a layer.
    ctx = _ctx(ArchUnitConfig())
    assert ctx.layer_of_path("models/staging/stg_customers.sql") == "staging"
    assert ctx.layer_of_path("models/marts/fct_orders.sql") == "marts"
    assert ctx.layer_of_path("models/reporting/rpt_revenue.sql") == "reporting"
    # A model directly under models/ (no subfolder) has no layer.
    assert ctx.layer_of_path("models/top_level.sql") is None


def test_auto_layers_can_be_disabled():
    ctx = _ctx(ArchUnitConfig(project=ProjectSettings(auto_layers=False)))
    assert ctx.layer_of_path("models/marts/fct_orders.sql") is None


def test_explicit_layers_win_over_auto():
    config = ArchUnitConfig(layers={"core": LayerDef(paths=["models/marts/**"])})
    ctx = _ctx(config)
    assert ctx.layer_of_path("models/marts/fct_orders.sql") == "core"  # explicit rename
    assert ctx.layer_of_path("models/staging/stg_customers.sql") == "staging"  # auto fallback


def test_inline_config_folds_into_config():
    # Rule params may be inline YAML keys instead of nested under `config:`.
    inline = RuleConfig.model_validate(
        {
            "name": "expect-max-lines-of-code",
            "max": 200,
            "ignore_comments": True,
            "include": ["models/**"],
        }
    )
    assert inline.config == {"max": 200, "ignore_comments": True}
    assert inline.include == ["models/**"]  # reserved key stays a field
    # The older nested form remains valid and equivalent.
    nested = RuleConfig.model_validate({"name": "expect-max-joins", "config": {"max": 7}})
    assert nested.config == {"max": 7}


def _layers_selected(ctx: ProjectContext, **rule_kwargs: object) -> set[str | None]:
    rule = RuleConfig(name="x", **rule_kwargs)
    return {ctx.layer_of_node(m) for m in ctx.models_for(rule)}


def test_scope_limits_to_listed_layers():
    ctx = _ctx(ArchUnitConfig())  # auto_layers -> staging/marts/reporting
    assert _layers_selected(ctx, scope=["marts"]) == {"marts"}
    assert _layers_selected(ctx, scope=["marts", "reporting"]) == {"marts", "reporting"}


def test_ignore_excludes_listed_layers():
    ctx = _ctx(ArchUnitConfig())
    assert _layers_selected(ctx, ignore=["staging"]) == {"marts", "reporting"}


def test_scope_and_ignore_compose():
    ctx = _ctx(ArchUnitConfig())
    assert _layers_selected(ctx, scope=["marts", "reporting"], ignore=["reporting"]) == {"marts"}


def test_no_scope_or_ignore_selects_all_layers():
    ctx = _ctx(ArchUnitConfig())
    assert _layers_selected(ctx) == {"staging", "marts", "reporting"}
