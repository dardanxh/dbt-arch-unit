"""Naming-convention rules (source: manifest + file paths)."""

from __future__ import annotations

import re
from collections.abc import Iterable

from dbt_arch_unit.config import RuleConfig
from dbt_arch_unit.context import ProjectContext
from dbt_arch_unit.rules import register
from dbt_arch_unit.violation import Violation

# Friendly aliases -> canonical case name.
_CASE_ALIASES = {
    "snake_case": "snake",
    "snake": "snake",
    "underscore": "snake",
    "kebab-case": "kebab",
    "kebab": "kebab",
    "kabob": "kebab",
    "hyphen": "kebab",
    "camelcase": "camel",
    "camel": "camel",
}
_CASE_PATTERNS = {
    "snake": re.compile(r"^[a-z0-9]+(_+[a-z0-9]+)*$"),  # stg_customers, stg_a__b
    "kebab": re.compile(r"^[a-z0-9]+(-+[a-z0-9]+)*$"),
    "camel": re.compile(r"^[a-z][a-zA-Z0-9]*$"),  # camelCase (starts lowercase)
}


@register(
    "expect-model-name-convention",
    "naming",
    "Model file names must follow a case convention, length, prefix, and suffix.",
    config_keys={
        "case": "snake_case / kebab-case / camelCase (aliases: underscore, kabob, camel)",
        "max_length": "maximum characters in the model name",
        "prefix": "required name prefix",
        "suffix": "required name suffix",
    },
)
def model_name_convention(ctx: ProjectContext, rule: RuleConfig) -> Iterable[Violation]:
    case = rule.config.get("case")
    max_length = rule.config.get("max_length")
    prefix = rule.config.get("prefix")
    suffix = rule.config.get("suffix")
    case_rx = _CASE_PATTERNS.get(_CASE_ALIASES.get(str(case).lower(), "")) if case else None
    for model in ctx.models_for(rule):
        name = model.name
        if case:
            if case_rx is None:
                yield ctx.violation(rule, model, f"unknown case convention '{case}'")
            elif not case_rx.fullmatch(name):
                yield ctx.violation(rule, model, f"'{name}' is not {case}")
        if max_length is not None and len(name) > max_length:
            yield ctx.violation(
                rule, model, f"'{name}' ({len(name)} chars) exceeds max {max_length}"
            )
        if prefix and not name.startswith(prefix):
            yield ctx.violation(rule, model, f"'{name}' must start with '{prefix}'")
        if suffix and not name.endswith(suffix):
            yield ctx.violation(rule, model, f"'{name}' must end with '{suffix}'")


@register(
    "expect-layer-name-prefix",
    "naming",
    "A model must carry its own layer's prefix and no other layer's (no misfiling).",
)
def layer_name_prefix(ctx: ProjectContext, rule: RuleConfig) -> Iterable[Violation]:
    prefix_to_layer: dict[str, str] = {}
    for layer_name, ldef in ctx.config.layers.items():
        for prefix in ldef.prefixes:
            prefix_to_layer[prefix] = layer_name
    for model in ctx.models_for(rule):
        layer = ctx.layer_of_node(model)
        if layer is None:
            continue
        prefixes = ctx.config.layers[layer].prefixes
        # 1) must carry one of its own layer's prefixes (when the layer defines any)
        if prefixes and not any(model.name.startswith(p) for p in prefixes):
            yield ctx.violation(
                rule, model, f"'{model.name}' must start with one of {prefixes} (layer '{layer}')"
            )
            continue
        # 2) must not carry a different layer's prefix (misfiled model)
        for prefix, intended in prefix_to_layer.items():
            if intended != layer and model.name.startswith(prefix):
                yield ctx.violation(
                    rule,
                    model,
                    f"'{model.name}' carries '{prefix}' prefix of layer '{intended}' "
                    f"but lives in layer '{layer}'",
                )
                break


@register(
    "expect-staging-name-matches-source",
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
    "expect-model-name-regex",
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
    "expect-column-naming",
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
