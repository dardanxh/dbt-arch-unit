"""Naming-convention rules (source: manifest + file paths)."""

from __future__ import annotations

import re
from collections.abc import Iterable

from dbt_arch_unit.config import RuleConfig
from dbt_arch_unit.context import ProjectContext
from dbt_arch_unit.rules import register
from dbt_arch_unit.violation import Violation


@register(
    "layer-name-prefix",
    "naming",
    "Model names must start with their layer's configured prefix.",
)
def layer_name_prefix(ctx: ProjectContext, rule: RuleConfig) -> Iterable[Violation]:
    for model in ctx.models_for(rule):
        layer = ctx.layer_of_node(model)
        if layer is None:
            continue
        prefixes = ctx.config.layers[layer].prefixes
        if prefixes and not any(model.name.startswith(p) for p in prefixes):
            yield ctx.violation(
                rule, model, f"'{model.name}' must start with one of {prefixes} (layer '{layer}')"
            )


@register(
    "directory-prefix-match",
    "naming",
    "A model's prefix must match the layer directory it lives in (no misfiling).",
)
def directory_prefix_match(ctx: ProjectContext, rule: RuleConfig) -> Iterable[Violation]:
    prefix_to_layer: dict[str, str] = {}
    for layer_name, layer in ctx.config.layers.items():
        for prefix in layer.prefixes:
            prefix_to_layer[prefix] = layer_name
    for model in ctx.models_for(rule):
        actual_layer = ctx.layer_of_node(model)
        for prefix, intended_layer in prefix_to_layer.items():
            if model.name.startswith(prefix) and actual_layer != intended_layer:
                yield ctx.violation(
                    rule,
                    model,
                    f"'{model.name}' has '{prefix}' prefix (layer '{intended_layer}') but lives "
                    f"in layer '{actual_layer}'",
                )
                break


@register(
    "staging-name-matches-source",
    "naming",
    "Staging model names must follow the stg_<source>__<table> pattern.",
    config_keys={"pattern": "template using {source} and {table} (default: stg_{source}__{table})"},
)
def staging_name_matches_source(ctx: ProjectContext, rule: RuleConfig) -> Iterable[Violation]:
    pattern = rule.config.get("pattern", "stg_{source}__{table}")
    layer = rule.config.get("layer", "staging")
    for model in ctx.models_for(rule):
        if ctx.layer_of_node(model) != layer:
            continue
        src_ids = [p for p in model.depends_on.nodes if p.startswith("source.")]
        if len(src_ids) != 1:
            continue
        src = ctx.manifest.sources[src_ids[0]]
        expected = pattern.format(source=src.source_name, table=src.name)
        if model.name != expected:
            yield ctx.violation(
                rule, model, f"'{model.name}' should be named '{expected}' for its source"
            )


@register(
    "model-name-regex",
    "naming",
    "Model names must match an allowed regex and avoid forbidden substrings.",
    config_keys={
        "allow": "regex the whole name must match",
        "forbid": "list of forbidden substrings (e.g. tmp, copy, final)",
    },
)
def model_name_regex(ctx: ProjectContext, rule: RuleConfig) -> Iterable[Violation]:
    allow = rule.config.get("allow")
    forbid = rule.config.get("forbid", [])
    allow_rx = re.compile(allow) if allow else None
    for model in ctx.models_for(rule):
        if allow_rx and not allow_rx.fullmatch(model.name):
            yield ctx.violation(rule, model, f"'{model.name}' does not match /{allow}/")
        for bad in forbid:
            if bad in model.name:
                yield ctx.violation(rule, model, f"'{model.name}' contains forbidden '{bad}'")


@register(
    "column-naming",
    "naming",
    "Columns of a given type must follow a naming pattern (needs data_type).",
    config_keys={
        "conventions": "list of {types: [...], pattern: regex} the column name must match"
    },
)
def column_naming(ctx: ProjectContext, rule: RuleConfig) -> Iterable[Violation]:
    conventions = rule.config.get("conventions", [])
    compiled = [(set(c.get("types", [])), re.compile(c["pattern"])) for c in conventions]
    for model in ctx.models_for(rule):
        for col in model.columns.values():
            if not col.data_type:
                continue
            dtype = col.data_type.lower()
            for types, rx in compiled:
                if any(t in dtype for t in types) and not rx.search(col.name):
                    yield ctx.violation(
                        rule,
                        model,
                        f"column '{col.name}' ({col.data_type}) must match /{rx.pattern}/",
                    )
