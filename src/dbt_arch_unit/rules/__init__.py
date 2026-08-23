"""Rule registry.

Each rule is a function `(ctx, rule_config) -> Iterable[Violation]` registered by
name via the `@register` decorator. Importing this package imports every rule
module so the registry is fully populated.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass

from dbt_arch_unit.config import RuleConfig
from dbt_arch_unit.context import ProjectContext
from dbt_arch_unit.violation import Violation

RuleFn = Callable[[ProjectContext, RuleConfig], Iterable[Violation]]


@dataclass(frozen=True)
class RuleMeta:
    name: str
    category: str
    description: str
    source: str  # "manifest" | "file" | "both"
    config_keys: dict[str, str]  # key -> human description of the config option


_REGISTRY: dict[str, tuple[RuleMeta, RuleFn]] = {}


def register(
    name: str,
    category: str,
    description: str,
    source: str = "manifest",
    config_keys: dict[str, str] | None = None,
) -> Callable[[RuleFn], RuleFn]:
    def decorator(fn: RuleFn) -> RuleFn:
        if name in _REGISTRY:
            raise ValueError(f"duplicate rule name: {name}")
        _REGISTRY[name] = (RuleMeta(name, category, description, source, config_keys or {}), fn)
        return fn

    return decorator


def get_rule(name: str) -> tuple[RuleMeta, RuleFn]:
    if name not in _REGISTRY:
        raise KeyError(name)
    return _REGISTRY[name]


def all_rules() -> list[RuleMeta]:
    return sorted((meta for meta, _ in _REGISTRY.values()), key=lambda m: (m.category, m.name))


def _load_all() -> None:
    """Import every rule module to populate the registry."""
    from dbt_arch_unit.rules import (  # noqa: F401
        dependencies,
        documentation,
        materialization,
        naming,
        style,
        testing,
    )


_load_all()
