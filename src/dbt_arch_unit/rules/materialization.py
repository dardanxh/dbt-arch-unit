"""Materialization & config-governance rules (source: manifest)."""

from __future__ import annotations

from collections.abc import Iterable

from dbt_arch_unit.config import RuleConfig
from dbt_arch_unit.context import ProjectContext
from dbt_arch_unit.rules import register
from dbt_arch_unit.violation import Violation


@register(
    "materialization-by-layer",
    "materialization",
    "Each layer must use an allow-listed materialization.",
    config_keys={"allow": "map of layer -> list of allowed materializations"},
)
def materialization_by_layer(ctx: ProjectContext, rule: RuleConfig) -> Iterable[Violation]:
    allow: dict[str, list[str]] = rule.config.get("allow", {})
    for model in ctx.models_for(rule):
        layer = ctx.layer_of_node(model)
        if layer is None or layer not in allow:
            continue
        mat = model.config.materialized or "view"
        if mat not in allow[layer]:
            yield ctx.violation(rule, model, f"'{layer}' model is '{mat}', allowed: {allow[layer]}")


@register(
    "incremental-requires-keys",
    "materialization",
    "Incremental models must set unique_key and on_schema_change.",
    config_keys={"require": "config keys that must be set (default: unique_key, on_schema_change)"},
)
def incremental_requires_keys(ctx: ProjectContext, rule: RuleConfig) -> Iterable[Violation]:
    required = rule.config.get("require", ["unique_key", "on_schema_change"])
    for model in ctx.models_for(rule):
        if model.config.materialized != "incremental":
            continue
        for key in required:
            value = getattr(model.config, key, None)
            if not value:
                yield ctx.violation(rule, model, f"incremental model missing '{key}'")


@register(
    "require-tags-by-layer",
    "materialization",
    "Models in a layer must carry the layer's required tags.",
    config_keys={"required": "map of layer -> list of tags every model must have"},
)
def require_tags_by_layer(ctx: ProjectContext, rule: RuleConfig) -> Iterable[Violation]:
    required: dict[str, list[str]] = rule.config.get("required", {})
    for model in ctx.models_for(rule):
        layer = ctx.layer_of_node(model)
        if layer is None or layer not in required:
            continue
        have = ctx._node_tags(model)
        missing = [t for t in required[layer] if t not in have]
        if missing:
            yield ctx.violation(rule, model, f"missing required tags {missing} for layer '{layer}'")


@register(
    "custom-schema-required",
    "materialization",
    "Models must target a custom schema, not the default.",
)
def custom_schema_required(ctx: ProjectContext, rule: RuleConfig) -> Iterable[Violation]:
    for model in ctx.models_for(rule):
        if not model.config.schema_name:
            yield ctx.violation(rule, model, "no custom schema configured (config.schema)")


@register(
    "max-ephemeral-models",
    "materialization",
    "The project may not exceed N ephemeral models.",
    config_keys={"max": "maximum number of ephemeral models (default: 5)"},
)
def max_ephemeral_models(ctx: ProjectContext, rule: RuleConfig) -> Iterable[Violation]:
    limit = rule.config.get("max", 5)
    ephemeral = [m for m in ctx.models_for(rule) if m.config.materialized == "ephemeral"]
    if len(ephemeral) > limit:
        names = ", ".join(sorted(m.name for m in ephemeral))
        yield ctx.violation(
            rule, "project", f"{len(ephemeral)} ephemeral models exceeds max {limit}: {names}"
        )
