"""The result type produced by every rule."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Severity(StrEnum):
    ERROR = "error"
    WARNING = "warning"


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
