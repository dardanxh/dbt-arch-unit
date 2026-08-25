"""Documentation-coverage rules (source: manifest)."""

from __future__ import annotations

from collections.abc import Iterable

from dbt_arch_unit.config import RuleConfig
from dbt_arch_unit.context import ProjectContext
from dbt_arch_unit.models.manifest import Node
from dbt_arch_unit.rules import register
from dbt_arch_unit.violation import Violation


@register(
    "expect-model-has-description",
    "documentation",
    "Every model must have a non-empty description.",
)
def model_has_description(ctx: ProjectContext, rule: RuleConfig) -> Iterable[Violation]:
    for model in ctx.models_for(rule):
        if not model.description.strip():
            yield ctx.violation(rule, model, "model has no description")


@register(
    "expect-column-has-description",
    "documentation",
    "Model columns must be documented (all columns, or just primary-key columns).",
    config_keys={"scope": "'all' or 'primary_key' (default: all)"},
)
def column_has_description(ctx: ProjectContext, rule: RuleConfig) -> Iterable[Violation]:
    scope = rule.config.get("scope", "all")
    for model in ctx.models_for(rule):
        target_cols = set(model.columns)
        if scope == "primary_key":
            target_cols = _pk_columns(ctx, model)
        for name in target_cols:
            col = model.columns.get(name)
            if col is not None and not col.description.strip():
                yield ctx.violation(rule, model, f"column '{name}' has no description")


def _pk_columns(ctx: ProjectContext, model: Node) -> set[str]:
    cols: set[str] = set()
    for test in ctx.tests_by_model.get(model.unique_id, []):
        if test.test_metadata and test.test_metadata.name in ("unique", "not_null"):
            col = test.column_name or test.test_metadata.kwargs.get("column_name")
            if col:
                cols.add(col)
    return cols


@register(
    "expect-exposure-has-owner",
    "documentation",
    "Every exposure must declare an owner and reference existing nodes.",
)
def exposure_has_owner(ctx: ProjectContext, rule: RuleConfig) -> Iterable[Violation]:
    known = set(ctx.manifest.nodes) | set(ctx.manifest.sources)
    for exp in ctx.exposures:
        if not (exp.owner.name or exp.owner.email):
            yield ctx.violation(rule, exp, f"exposure '{exp.name}' has no owner")
        missing = [d for d in exp.depends_on.nodes if d not in known]
        if missing:
            yield ctx.violation(
                rule, exp, f"exposure '{exp.name}' references unknown nodes: {missing}"
            )


@register(
    "expect-model-has-owner-meta",
    "documentation",
    "Every model must declare an owner in its meta.",
    config_keys={"key": "the meta key that must be present (default: owner)"},
)
def model_has_owner_meta(ctx: ProjectContext, rule: RuleConfig) -> Iterable[Violation]:
    key = rule.config.get("key", "owner")
    for model in ctx.models_for(rule):
        if not (model.meta.get(key) or model.config.meta.get(key)):
            yield ctx.violation(rule, model, f"missing meta.{key}")
