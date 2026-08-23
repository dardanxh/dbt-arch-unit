"""Rendering of results: Rich tables, JSON, and summaries."""

from __future__ import annotations

import json

from rich.console import Console
from rich.table import Table

from dbt_arch_unit.runner import RunResult
from dbt_arch_unit.violation import Severity, Violation

_STYLE = {Severity.ERROR: "bold red", Severity.WARNING: "yellow"}


def _location(v: Violation) -> str:
    if not v.path:
        return v.node
    return f"{v.path}:{v.line}" if v.line else v.path


def render_table(result: RunResult, console: Console) -> None:
    if result.unknown_rules:
        console.print(
            f"[yellow]warning:[/] unknown rules ignored: {', '.join(result.unknown_rules)}"
        )
    if not result.violations:
        console.print("[bold green]✓ All architecture rules passed.[/]")
        return

    table = Table(show_lines=False, header_style="bold")
    table.add_column("severity")
    table.add_column("rule", style="cyan")
    table.add_column("location", style="dim")
    table.add_column("message")
    for v in sorted(result.violations, key=lambda x: (x.severity.value, x.rule)):
        table.add_row(
            f"[{_STYLE[v.severity]}]{v.severity}[/]",
            v.rule,
            _location(v),
            v.message,
        )
    console.print(table)
    console.print(f"\n[bold]{len(result.errors)} error(s), {len(result.warnings)} warning(s)[/]")


def render_json(result: RunResult) -> str:
    payload = {
        "summary": {
            "errors": len(result.errors),
            "warnings": len(result.warnings),
            "unknown_rules": result.unknown_rules,
        },
        "violations": [v.to_dict() for v in result.violations],
    }
    return json.dumps(payload, indent=2)
