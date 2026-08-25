"""Heuristic facts extracted from a model's raw SQL.

We are not building a full SQL parser. dbt SQL is Jinja-templated and dialect-
specific, so instead we strip Jinja/comments/strings and use robust regex probes
that answer the specific questions the style rules ask (LOC, CTE count, joins,
`select *`, final column count, hardcoded refs).
"""

from __future__ import annotations

import re
from functools import cached_property

_JINJA_COMMENT = re.compile(r"{#.*?#}", re.S)
_JINJA_EXPR = re.compile(r"{{.*?}}", re.S)
_JINJA_STMT = re.compile(r"{%.*?%}", re.S)
_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.S)
_LINE_COMMENT = re.compile(r"--[^\n]*")
_STRING_LITERAL = re.compile(r"'(?:[^']|'')*'")

_CTE = re.compile(r"(?:\bwith\b|,)\s+([a-zA-Z_]\w*)\s+as\s*\(", re.I)
_SELECT = re.compile(r"\bselect\b", re.I)
_STAR = re.compile(r"\bselect\s+(?:distinct\s+)?\*", re.I)
_JOIN = re.compile(r"\bjoin\b", re.I)
_FROM = re.compile(r"\bfrom\b", re.I)
_DOTTED_REF = re.compile(r"\b(?:from|join)\s+([a-z_]\w*(?:\.\w+)+)", re.I)

_JINJA_PLACEHOLDER = "__ref__"


class ParsedSql:
    """Lazily-computed, cached facts about one model's SQL."""

    def __init__(self, raw: str):
        self.raw = raw

    @cached_property
    def clean(self) -> str:
        """SQL with comments and strings removed and Jinja neutralised."""
        s = _JINJA_COMMENT.sub(" ", self.raw)
        s = _JINJA_EXPR.sub(_JINJA_PLACEHOLDER, s)
        s = _JINJA_STMT.sub(" ", s)
        s = _BLOCK_COMMENT.sub(" ", s)
        s = _LINE_COMMENT.sub(" ", s)
        s = _STRING_LITERAL.sub("''", s)
        return s

    def loc(self, ignore_comments: bool = True) -> int:
        """Non-blank line count. When ignore_comments, drop comment-only lines."""
        count = 0
        for line in self.raw.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if ignore_comments and stripped.startswith(("--", "#")):
                continue
            count += 1
        return count

    @cached_property
    def line_comments(self) -> list[str]:
        """Text of each `-- ...` comment (marker stripped). Regex over raw SQL, so a
        `--` inside a string literal is a rare false positive."""
        return [m.group(0)[2:].strip() for m in _LINE_COMMENT.finditer(self.raw)]

    @cached_property
    def block_comments(self) -> list[str]:
        """Text of each `/* ... */` comment (delimiters stripped)."""
        return [m.group(0)[2:-2].strip() for m in _BLOCK_COMMENT.finditer(self.raw)]

    @cached_property
    def comments(self) -> list[str]:
        """All comments (line + block), delimiters stripped."""
        return self.line_comments + self.block_comments

    @cached_property
    def cte_names(self) -> list[str]:
        return [m.lower() for m in _CTE.findall(self.clean)]

    @cached_property
    def join_count(self) -> int:
        return len(_JOIN.findall(self.clean))

    def _selects_at_depth_zero(self) -> list[int]:
        """Positions of `select` keywords sitting outside any parentheses."""
        depth_at: list[int] = []
        depths = self._paren_depths()
        for m in _SELECT.finditer(self.clean):
            if depths[m.start()] == 0:
                depth_at.append(m.start())
        return depth_at

    def _paren_depths(self) -> list[int]:
        depths = [0] * (len(self.clean) + 1)
        depth = 0
        for i, ch in enumerate(self.clean):
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth = max(0, depth - 1)
            depths[i] = depth
        return depths

    def has_select_star(self, allow_in_ctes: bool = True) -> bool:
        if not _STAR.search(self.clean):
            return False
        if not allow_in_ctes:
            return True
        # Only flag a star in the final (depth-0) projection.
        for pos in self._selects_at_depth_zero():
            m = _STAR.match(self.clean, pos)
            if m:
                return True
        return False

    @cached_property
    def final_column_count(self) -> int:
        """Best-effort count of columns in the outermost SELECT list."""
        zero = self._selects_at_depth_zero()
        select_pos = zero[-1] if zero else (self._first_select_pos())
        if select_pos is None:
            return 0
        start = select_pos + len("select")
        from_m = _FROM.search(self.clean, start)
        end = from_m.start() if from_m else len(self.clean)
        projection = self.clean[start:end]
        return self._count_top_level_columns(projection)

    def _first_select_pos(self) -> int | None:
        m = _SELECT.search(self.clean)
        return m.start() if m else None

    @staticmethod
    def _count_top_level_columns(projection: str) -> int:
        projection = projection.strip()
        if not projection or projection.strip().startswith("*"):
            return 1 if projection else 0
        depth = 0
        columns = 1
        for ch in projection:
            if ch in "([":
                depth += 1
            elif ch in ")]":
                depth = max(0, depth - 1)
            elif ch == "," and depth == 0:
                columns += 1
        return columns

    @cached_property
    def hardcoded_refs(self) -> list[str]:
        """`from`/`join` targets that are dotted identifiers, not ref()/source()."""
        found = []
        for ident in _DOTTED_REF.findall(self.clean):
            if _JINJA_PLACEHOLDER in ident.lower():
                continue
            found.append(ident)
        return found

    @cached_property
    def cross_database_refs(self) -> list[str]:
        return [r for r in self.hardcoded_refs if r.count(".") >= 2]
