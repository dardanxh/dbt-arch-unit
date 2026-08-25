"""Layering & dependency rules (source: manifest)."""

from __future__ import annotations

from collections.abc import Iterable

from dbt_arch_unit.config import RuleConfig
from dbt_arch_unit.context import ProjectContext
from dbt_arch_unit.models.manifest import Node
from dbt_arch_unit.rules import register
from dbt_arch_unit.violation import Violation


def _model_parents(ctx: ProjectContext, node: Node) -> list[str]:
    return [p for p in node.depends_on.nodes if p in ctx.manifest.nodes]


def _source_parents(node: Node) -> list[str]:
    return [p for p in node.depends_on.nodes if p.startswith("source.")]


def _edges(chains: list[str]) -> set[tuple[str, str]]:
    """Parse 'a > b > c' flow chains into adjacent (upstream, downstream) edges.

    Data flows left -> right, so an edge (a, b) means 'b may depend on a'.
    """
    out: set[tuple[str, str]] = set()
    for chain in chains:
        toks = [t.strip() for t in chain.split(">") if t.strip()]
        out.update(zip(toks, toks[1:], strict=False))
    return out


@register(
    "test-dependencies",
    "dependencies",
    "Layer dependencies must follow allow-listed flow chains (and avoid denied ones).",
    config_keys={
        "allow": "list of 'a > b > c' flow chains a layer may depend on (adjacent only)",
        "deny": "list of 'a > b' flow chains that are forbidden",
    },
)
def test_dependencies(ctx: ProjectContext, rule: RuleConfig) -> Iterable[Violation]:
    allow_edges = _edges(rule.config.get("allow", []))
    deny_edges = _edges(rule.config.get("deny", []))
    if not allow_edges and not deny_edges:
        return
    for model in ctx.models_for(rule):
        layer = ctx.layer_of_node(model)
        if layer is None:
            continue
        for parent in model.depends_on.nodes:
            player = ctx.layer_for_id(parent)
            if player is None:
                continue
            edge = (player, layer)  # parent flows into model: 'player > layer'
            denied = edge in deny_edges
            not_allowed = bool(allow_edges) and edge not in allow_edges
            if denied or not_allowed:
                yield ctx.violation(
                    rule, model, f"'{layer}' model depends on '{player}' ({parent})"
                )


@register(
    "forbidden-dependencies",
    "dependencies",
    "Explicit deny-list of (from_layer, to_layer) dependency pairs.",
    config_keys={"deny": "list of [from_layer, to_layer] pairs that are forbidden"},
)
def forbidden_dependencies(ctx: ProjectContext, rule: RuleConfig) -> Iterable[Violation]:
    deny = {(a, b) for a, b in rule.config.get("deny", [])}
    for model in ctx.models_for(rule):
        layer = ctx.layer_of_node(model)
        for parent in model.depends_on.nodes:
            player = ctx.layer_for_id(parent)
            if layer and player and (layer, player) in deny:
                yield ctx.violation(
                    rule, model, f"forbidden dependency '{layer}' -> '{player}' ({parent})"
                )


@register(
    "sources-only-in-staging",
    "dependencies",
    "Raw sources may only be referenced by the staging layer.",
    config_keys={"layer": "the single layer allowed to read sources (default: staging)"},
)
def sources_only_in_staging(ctx: ProjectContext, rule: RuleConfig) -> Iterable[Violation]:
    entry = rule.config.get("layer", "staging")
    for model in ctx.models_for(rule):
        if ctx.layer_of_node(model) == entry:
            continue
        for src in _source_parents(model):
            yield ctx.violation(
                rule, model, f"non-{entry} model references source directly ({src})"
            )


@register(
    "staging-one-source",
    "dependencies",
    "Each staging model references exactly one source and no other models.",
)
def staging_one_source(ctx: ProjectContext, rule: RuleConfig) -> Iterable[Violation]:
    for model in ctx.models_for(rule):
        if ctx.layer_of_node(model) != rule.config.get("layer", "staging"):
            continue
        sources = _source_parents(model)
        models = _model_parents(ctx, model)
        if len(sources) != 1 or models:
            yield ctx.violation(
                rule,
                model,
                f"staging model should reference exactly one source and no models "
                f"(found {len(sources)} sources, {len(models)} models)",
            )


@register(
    "no-orphan-models",
    "dependencies",
    "Every model must be consumed by another model or an exposure.",
    config_keys={"allow_tags": "tags marking intentionally-terminal models"},
)
def no_orphan_models(ctx: ProjectContext, rule: RuleConfig) -> Iterable[Violation]:
    allow_tags = set(rule.config.get("allow_tags", []))
    consumed: set[str] = set()
    for node in ctx.models:
        consumed.update(_model_parents(ctx, node))
    for exp in ctx.exposures:
        consumed.update(exp.depends_on.nodes)
    for model in ctx.models_for(rule):
        if model.unique_id in consumed:
            continue
        if allow_tags & ctx._node_tags(model):
            continue
        yield ctx.violation(rule, model, "orphan model: not consumed by any model or exposure")


@register(
    "max-fan-in",
    "dependencies",
    "A model may not have more than N direct parents.",
    config_keys={"max": "maximum number of direct parents (default: 10)"},
)
def max_fan_in(ctx: ProjectContext, rule: RuleConfig) -> Iterable[Violation]:
    limit = rule.config.get("max", 10)
    for model in ctx.models_for(rule):
        parents = len(model.depends_on.nodes)
        if parents > limit:
            yield ctx.violation(rule, model, f"{parents} parents exceeds max {limit}")


@register(
    "max-fan-out",
    "dependencies",
    "A model may not have more than N direct model children.",
    config_keys={"max": "maximum number of direct children (default: 20)"},
)
def max_fan_out(ctx: ProjectContext, rule: RuleConfig) -> Iterable[Violation]:
    limit = rule.config.get("max", 20)
    children: dict[str, int] = {}
    for node in ctx.models:
        for parent in _model_parents(ctx, node):
            children[parent] = children.get(parent, 0) + 1
    for model in ctx.models_for(rule):
        count = children.get(model.unique_id, 0)
        if count > limit:
            yield ctx.violation(rule, model, f"{count} children exceeds max {limit}")


@register(
    "no-cross-domain-refs",
    "dependencies",
    "Models may only reference another domain through the boundary layer.",
    config_keys={
        "domain_segment": "path index identifying the domain (default: 2)",
        "boundary_layer": "layer allowed to be shared across domains (default: marts)",
    },
)
def no_cross_domain_refs(ctx: ProjectContext, rule: RuleConfig) -> Iterable[Violation]:
    seg = rule.config.get("domain_segment", 2)
    boundary = rule.config.get("boundary_layer", "marts")

    def domain(node: Node) -> str | None:
        parts = node.original_file_path.split("/")
        return parts[seg] if len(parts) > seg + 1 else None

    for model in ctx.models_for(rule):
        my_domain = domain(model)
        if my_domain is None:
            continue
        for parent in _model_parents(ctx, model):
            pnode = ctx.manifest.nodes[parent]
            pdomain = domain(pnode)
            if pdomain and pdomain != my_domain and ctx.layer_of_node(pnode) != boundary:
                yield ctx.violation(
                    rule,
                    model,
                    f"cross-domain reference '{my_domain}' -> '{pdomain}' via non-{boundary} "
                    f"model ({parent})",
                )


@register(
    "max-dependency-depth",
    "dependencies",
    "The longest path from a source to a model may not exceed N.",
    config_keys={"max": "maximum dependency depth (default: 5)"},
)
def max_dependency_depth(ctx: ProjectContext, rule: RuleConfig) -> Iterable[Violation]:
    limit = rule.config.get("max", 5)
    depth: dict[str, int] = {}

    def compute(uid: str, stack: frozenset[str]) -> int:
        if uid in depth:
            return depth[uid]
        if uid in stack:  # cycle guard
            return 0
        node = ctx.manifest.nodes.get(uid)
        if node is None or not node.is_model:
            return 0
        parents = _model_parents(ctx, node)
        d = 1 + max((compute(p, stack | {uid}) for p in parents), default=0)
        depth[uid] = d
        return d

    for model in ctx.models_for(rule):
        d = compute(model.unique_id, frozenset())
        if d > limit:
            yield ctx.violation(rule, model, f"dependency depth {d} exceeds max {limit}")


@register(
    "no-model-cycles",
    "dependencies",
    "The model dependency graph must be acyclic.",
)
def no_model_cycles(ctx: ProjectContext, rule: RuleConfig) -> Iterable[Violation]:
    WHITE, GREY, BLACK = 0, 1, 2
    color: dict[str, int] = {}
    reported: set[str] = set()

    def visit(uid: str) -> None:
        color[uid] = GREY
        node = ctx.manifest.nodes.get(uid)
        for parent in _model_parents(ctx, node) if node else []:
            state = color.get(parent, WHITE)
            if state == GREY and parent not in reported:
                reported.add(parent)
            elif state == WHITE:
                visit(parent)
        color[uid] = BLACK

    for model in ctx.models:
        if color.get(model.unique_id, WHITE) == WHITE:
            visit(model.unique_id)

    in_scope = {m.unique_id for m in ctx.models_for(rule)}
    for uid in reported & in_scope:
        node = ctx.manifest.nodes[uid]
        yield ctx.violation(rule, node, "model participates in a dependency cycle")
