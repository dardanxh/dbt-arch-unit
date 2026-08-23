"""Testing & quality-gate rules (source: manifest)."""

from __future__ import annotations

from collections.abc import Iterable

from dbt_arch_unit.config import RuleConfig
from dbt_arch_unit.context import ProjectContext
from dbt_arch_unit.rules import register
from dbt_arch_unit.violation import Violation


@register(
    "min-tests-per-model",
    "testing",
    "Every model must have at least N data tests.",
    config_keys={"min": "minimum number of data tests per model (default: 1)"},
)
def min_tests_per_model(ctx: ProjectContext, rule: RuleConfig) -> Iterable[Violation]:
    minimum = rule.config.get("min", 1)
    for model in ctx.models_for(rule):
        count = len(ctx.tests_by_model.get(model.unique_id, []))
        if count < minimum:
            yield ctx.violation(rule, model, f"has {count} tests, requires at least {minimum}")


@register(
    "require-primary-key",
    "testing",
    "Every model must have a unique + not_null pair defining its primary key.",
)
def require_primary_key(ctx: ProjectContext, rule: RuleConfig) -> Iterable[Violation]:
    for model in ctx.models_for(rule):
        if not ctx.has_pk_test(model):
            yield ctx.violation(
                rule, model, "missing primary key (needs unique + not_null on a column)"
            )


@register(
    "require-unit-tests",
    "testing",
    "Models in scope must have at least one dbt unit test.",
    config_keys={"min": "minimum number of unit tests (default: 1)"},
)
def require_unit_tests(ctx: ProjectContext, rule: RuleConfig) -> Iterable[Violation]:
    minimum = rule.config.get("min", 1)
    for model in ctx.models_for(rule):
        count = ctx.unit_tests_by_model.get(model.unique_id, 0)
        if count < minimum:
            yield ctx.violation(rule, model, f"has {count} unit tests, requires at least {minimum}")


@register(
    "source-freshness",
    "testing",
    "Every source must configure freshness (and a loaded_at_field).",
    source="manifest",
    config_keys={"require_loaded_at": "also require loaded_at_field (default: true)"},
)
def source_freshness(ctx: ProjectContext, rule: RuleConfig) -> Iterable[Violation]:
    require_loaded_at = rule.config.get("require_loaded_at", True)
    for src in ctx.sources:
        if not src.has_freshness:
            yield ctx.violation(
                rule, src, f"source '{src.source_name}.{src.name}' has no freshness configured"
            )
        elif require_loaded_at and not src.loaded_at_field:
            yield ctx.violation(
                rule, src, f"source '{src.source_name}.{src.name}' has no loaded_at_field"
            )


@register(
    "no-disabled-nodes",
    "testing",
    "No disabled models should linger in the project.",
)
def no_disabled_nodes(ctx: ProjectContext, rule: RuleConfig) -> Iterable[Violation]:
    include = ctx.config.effective_include(rule)
    for entries in ctx.manifest.disabled.values():
        for entry in entries:
            if entry.get("resource_type") != "model":
                continue
            path = entry.get("original_file_path", "")
            if any(ctx._match(p, path) for p in include):
                yield ctx.violation(
                    rule, entry.get("unique_id", entry.get("name", "?")), f"disabled model: {path}"
                )


@register(
    "require-contract",
    "testing",
    "Models in scope must enforce a data contract.",
)
def require_contract(ctx: ProjectContext, rule: RuleConfig) -> Iterable[Violation]:
    for model in ctx.models_for(rule):
        if not model.config.contract.enforced:
            yield ctx.violation(rule, model, "contract not enforced (config.contract.enforced)")
