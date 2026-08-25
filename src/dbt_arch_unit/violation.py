"""The result type produced by every rule."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Severity(str, Enum):
    # str-Enum (not enum.StrEnum) to keep compatibility with Python 3.10.
    ERROR = "error"
    WARNING = "warning"

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class Violation:
    rule: str
    severity: Severity
    message: str
    node: str  # unique_id or logical name of the offending object
    path: str = ""  # file path, for click-through
    line: int | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "rule": self.rule,
            "severity": self.severity.value,
            "message": self.message,
            "node": self.node,
            "path": self.path,
            "line": self.line,
        }
