"""Code-style & complexity rules (source: raw SQL files)."""

from __future__ import annotations

from collections.abc import Iterable

from dbt_arch_unit.config import RuleConfig
from dbt_arch_unit.context import ProjectContext
from dbt_arch_unit.rules import register
from dbt_arch_unit.violation import Violation


@register(
    "expect-comments",
    "style",
    "SQL comments must follow the configured policy.",
    source="file",
    config_keys={
        "allowed": "are comments permitted at all (default: true)",
        "max_length": "max characters allowed in a single comment",
        "allow_block": "permit /* */ block comments (default: true)",
        "forbid": "forbidden substrings, e.g. [TODO, FIXME] (case-insensitive)",
    },
)
def comments(ctx: ProjectContext, rule: RuleConfig) -> Iterable[Violation]:
    allowed = rule.config.get("allowed", True)
    allow_block = rule.config.get("allow_block", True)
    max_length = rule.config.get("max_length")
    forbid = [f.lower() for f in rule.config.get("forbid", [])]
    for model in ctx.models_for(rule):
        sql = ctx.sql(model)
        all_comments = sql.comments
        if not allowed:
            if all_comments:
                n = len(all_comments)
                yield ctx.violation(rule, model, f"comments are not allowed ({n} found)")
            continue
        if not allow_block and sql.block_comments:
            yield ctx.violation(rule, model, "block comments (/* */) are not allowed")
        for comment in all_comments:
            if max_length is not None and len(comment) > max_length:
                snippet = comment[:30] + ("…" if len(comment) > 30 else "")
                yield ctx.violation(
                    rule, model, f"comment exceeds {max_length} chars ({len(comment)}): '{snippet}'"
                )
            low = comment.lower()
            for bad in forbid:
                if bad in low:
                    yield ctx.violation(rule, model, f"comment contains forbidden '{bad}'")


@register(
    "expect-max-lines-of-code",
    "style",
    "A model's SQL must not exceed a maximum line count.",
    source="file",
    config_keys={"max": "maximum lines (default: 200)", "ignore_comments": "default: true"},
)
def max_lines_of_code(ctx: ProjectContext, rule: RuleConfig) -> Iterable[Violation]:
    limit = rule.config.get("max", 200)
    ignore_comments = rule.config.get("ignore_comments", True)
    for model in ctx.models_for(rule):
        loc = ctx.sql(model).loc(ignore_comments=ignore_comments)
        if loc > limit:
            yield ctx.violation(rule, model, f"{loc} lines of code exceeds max {limit}")


@register(
    "expect-max-columns",
    "style",
    "A model's outermost SELECT may not project more than N columns.",
    source="file",
    config_keys={"max": "maximum columns in the final SELECT (default: 50)"},
)
def max_columns(ctx: ProjectContext, rule: RuleConfig) -> Iterable[Violation]:
    limit = rule.config.get("max", 50)
    for model in ctx.models_for(rule):
        cols = ctx.sql(model).final_column_count
        if cols > limit:
            yield ctx.violation(rule, model, f"{cols} columns exceeds max {limit}")


@register(
    "expect-no-select-star",
    "style",
    "Models must not use `select *` in their final projection.",
    source="file",
    config_keys={"allow_in_ctes": "permit `select *` inside CTEs (default: true)"},
)
def no_select_star(ctx: ProjectContext, rule: RuleConfig) -> Iterable[Violation]:
    allow_in_ctes = rule.config.get("allow_in_ctes", True)
    for model in ctx.models_for(rule):
        if ctx.sql(model).has_select_star(allow_in_ctes=allow_in_ctes):
            yield ctx.violation(rule, model, "uses `select *`")


@register(
    "expect-max-ctes",
    "style",
    "A model may not contain more than N CTEs.",
    source="file",
    config_keys={"max": "maximum number of CTEs (default: 10)"},
)
def max_ctes(ctx: ProjectContext, rule: RuleConfig) -> Iterable[Violation]:
    limit = rule.config.get("max", 10)
    for model in ctx.models_for(rule):
        count = len(ctx.sql(model).cte_names)
        if count > limit:
            yield ctx.violation(rule, model, f"{count} CTEs exceeds max {limit}")


@register(
    "expect-max-joins",
    "style",
    "A model may not contain more than N joins.",
    source="file",
    config_keys={"max": "maximum number of joins (default: 7)"},
)
def max_joins(ctx: ProjectContext, rule: RuleConfig) -> Iterable[Violation]:
    limit = rule.config.get("max", 7)
    for model in ctx.models_for(rule):
        count = ctx.sql(model).join_count
        if count > limit:
            yield ctx.violation(rule, model, f"{count} joins exceeds max {limit}")


@register(
    "expect-no-hardcoded-refs",
    "style",
    "Models must reference tables via ref()/source(), not hardcoded schema.table.",
    source="file",
)
def require_ref_not_hardcoded(ctx: ProjectContext, rule: RuleConfig) -> Iterable[Violation]:
    for model in ctx.models_for(rule):
        hardcoded = ctx.sql(model).hardcoded_refs
        if hardcoded:
            refs = sorted(set(hardcoded))
            yield ctx.violation(rule, model, f"hardcoded table references: {refs}")


@register(
    "expect-no-cross-database-refs",
    "style",
    "Models must not reference fully database-qualified identifiers.",
    source="file",
)
def no_cross_database_refs(ctx: ProjectContext, rule: RuleConfig) -> Iterable[Violation]:
    for model in ctx.models_for(rule):
        cross = ctx.sql(model).cross_database_refs
        if cross:
            yield ctx.violation(rule, model, f"cross-database references: {sorted(set(cross))}")


@register(
    "expect-import-cte-structure",
    "style",
    "Multi-ref models should use import CTEs rather than inline references.",
    source="file",
    config_keys={"min_refs": "parents above which CTEs are required (default: 1)"},
)
def require_import_cte_structure(ctx: ProjectContext, rule: RuleConfig) -> Iterable[Violation]:
    threshold = rule.config.get("min_refs", 1)
    for model in ctx.models_for(rule):
        parents = len(model.depends_on.nodes)
        if parents > threshold and not ctx.sql(model).cte_names:
            yield ctx.violation(
                rule, model, f"references {parents} parents but defines no import CTEs"
            )
