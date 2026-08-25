"""ProjectContext — the shared, pre-computed view every rule reads from.

Built once per run. Centralises layer resolution, selector/scoping logic, cached
SQL parsing and test indexes so individual rule functions stay tiny.
"""

from __future__ import annotations

import re
from functools import cached_property
from pathlib import Path

from dbt_arch_unit.config import ArchUnitConfig, RuleConfig
from dbt_arch_unit.models.manifest import Exposure, Manifest, Node, Source
from dbt_arch_unit.parsers.project_parser import read_model_source
from dbt_arch_unit.parsers.sql_parser import ParsedSql
from dbt_arch_unit.violation import Violation

SOURCE_LAYER = "source"


def _glob_to_regex(pattern: str) -> re.Pattern[str]:
    i, out = 0, ""
    while i < len(pattern):
        if pattern[i : i + 2] == "**":
            out += ".*"
            i += 2
            if i < len(pattern) and pattern[i] == "/":
                i += 1
        elif pattern[i] == "*":
            out += "[^/]*"
            i += 1
        elif pattern[i] == "?":
            out += "[^/]"
            i += 1
        else:
            out += re.escape(pattern[i])
            i += 1
    return re.compile("^" + out + "$")


class ProjectContext:
    def __init__(self, config: ArchUnitConfig, manifest: Manifest):
        self.config = config
        self.manifest = manifest
        self.project_dir = Path(config.project.dir).resolve()
        self._glob_cache: dict[str, re.Pattern[str]] = {}
        self._sql_cache: dict[str, ParsedSql] = {}

    # -- collections -------------------------------------------------------

    @cached_property
    def models(self) -> list[Node]:
        return [n for n in self.manifest.nodes.values() if n.resource_type == "model"]

    @cached_property
    def data_tests(self) -> list[Node]:
        return [n for n in self.manifest.nodes.values() if n.resource_type == "test"]

    @property
    def sources(self) -> list[Source]:
        return list(self.manifest.sources.values())

    @property
    def exposures(self) -> list[Exposure]:
        return list(self.manifest.exposures.values())

    # -- layers ------------------------------------------------------------

    def _match(self, pattern: str, path: str) -> bool:
        rx = self._glob_cache.get(pattern)
        if rx is None:
            rx = self._glob_to_regex_cached(pattern)
        return bool(rx.match(path))

    def _glob_to_regex_cached(self, pattern: str) -> re.Pattern[str]:
        rx = _glob_to_regex(pattern)
        self._glob_cache[pattern] = rx
        return rx

    def layer_of_path(self, path: str) -> str | None:
        for name, layer in self.config.layers.items():
            if any(self._match(p, path) for p in layer.paths):
                return name
        if self.config.project.auto_layers:
            return self._folder_layer(path)
        return None

    def _folder_layer(self, path: str) -> str | None:
        """Derive a layer name from the top folder under models_path.

        e.g. 'models/datamart/fact_x.sql' -> 'datamart'. Models sitting directly
        in models_path (no subfolder) have no layer.
        """
        prefix = self.config.project.models_path.strip("/") + "/"
        normalized = path.replace("\\", "/")
        if not normalized.startswith(prefix):
            return None
        rest = normalized[len(prefix) :].split("/")
        return rest[0] if len(rest) >= 2 else None

    def layer_of_node(self, node: Node) -> str | None:
        return self.layer_of_path(node.original_file_path)

    def layer_for_id(self, unique_id: str) -> str | None:
        """Layer for any parent id — sources collapse to the 'source' layer."""
        if unique_id.startswith("source."):
            return SOURCE_LAYER
        node = self.manifest.nodes.get(unique_id)
        return self.layer_of_node(node) if node and node.is_model else None

    # -- selectors ---------------------------------------------------------

    def models_for(self, rule: RuleConfig) -> list[Node]:
        include = self.config.effective_include(rule)
        exclude = self.config.effective_exclude(rule)
        types = rule.resource_types or ["model"]
        result = []
        for node in self.manifest.nodes.values():
            if node.resource_type not in types:
                continue
            path = node.original_file_path
            if not any(self._match(p, path) for p in include):
                continue
            if any(self._match(p, path) for p in exclude):
                continue
            layer = self.layer_of_node(node)
            if rule.scope and layer not in rule.scope:
                continue
            if rule.ignore and layer in rule.ignore:
                continue
            if rule.tags and not (set(rule.tags) & self._node_tags(node)):
                continue
            result.append(node)
        return result

    @staticmethod
    def _node_tags(node: Node) -> set[str]:
        return set(node.tags) | set(node.config.tags)

    # -- sql ---------------------------------------------------------------

    def sql(self, node: Node) -> ParsedSql:
        parsed = self._sql_cache.get(node.unique_id)
        if parsed is None:
            raw = read_model_source(self.project_dir, node.original_file_path, node.raw_code)
            parsed = ParsedSql(raw)
            self._sql_cache[node.unique_id] = parsed
        return parsed

    # -- test indexes ------------------------------------------------------

    @cached_property
    def tests_by_model(self) -> dict[str, list[Node]]:
        index: dict[str, list[Node]] = {}
        for test in self.data_tests:
            for parent in test.depends_on.nodes:
                index.setdefault(parent, []).append(test)
        return index

    @cached_property
    def unit_tests_by_model(self) -> dict[str, int]:
        index: dict[str, int] = {}
        for ut in self.manifest.unit_tests.values():
            target = ut.model or next(iter(ut.depends_on.nodes), None)
            if target:
                index[target] = index.get(target, 0) + 1
        return index

    def has_pk_test(self, model: Node) -> bool:
        """True if the model has a unique + not_null pair on a shared column."""
        uniques, not_nulls = set(), set()
        for test in self.tests_by_model.get(model.unique_id, []):
            meta = test.test_metadata
            if meta is None:
                continue
            col = test.column_name or meta.kwargs.get("column_name")
            if meta.name == "unique":
                uniques.add(col)
            elif meta.name == "not_null":
                not_nulls.add(col)
        return bool(uniques & not_nulls) or (bool(uniques) and None in not_nulls)

    # -- violation factory -------------------------------------------------

    def violation(
        self,
        rule: RuleConfig,
        obj: Node | Source | Exposure | str,
        message: str,
        line: int | None = None,
    ) -> Violation:
        if isinstance(obj, str):
            node_id, path = obj, ""
        else:
            node_id = obj.unique_id
            path = getattr(obj, "original_file_path", "")
        return Violation(
            rule=rule.name,
            severity=self.config.effective_severity(rule),
            message=message,
            node=node_id,
            path=path,
            line=line,
        )
