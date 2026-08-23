"""Typer CLI: check / list-rules / explain / init."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from dbt_arch_unit import __version__
from dbt_arch_unit.config import (
    CONFIG_FILENAME,
    ArchUnitConfig,
    ConfigError,
    find_config,
    load_config,
)
from dbt_arch_unit.context import ProjectContext
from dbt_arch_unit.html_report import render_html
from dbt_arch_unit.parsers.manifest_parser import ManifestError
from dbt_arch_unit.reporting import render_json, render_table
from dbt_arch_unit.rules import all_rules, get_rule
from dbt_arch_unit.runner import RunResult, build_context, run
from dbt_arch_unit.scaffold import inspect_dbt_project, render_config

app = typer.Typer(
    add_completion=False,
    help="Architectural unit testing for dbt projects.",
    no_args_is_help=True,
)
console = Console()
err_console = Console(stderr=True)


def _load_and_run(
    config: Path | None,
    project_dir: Path | None,
    manifest: Path | None,
    select: str | None,
) -> tuple[ArchUnitConfig, ProjectContext, RunResult]:
    """Resolve config, build the context, run the rules. Exits on user errors."""
    config_path = config or find_config(Path.cwd())
    if config_path is None:
        err_console.print(f"[red]error:[/] no {CONFIG_FILENAME} found. Run `dbt-arch-unit init`.")
        raise typer.Exit(2)

    try:
        cfg = load_config(config_path)
    except ConfigError as exc:
        err_console.print(f"[red]error:[/] {exc}")
        raise typer.Exit(2) from exc

    if project_dir is not None:
        cfg.project.dir = str(project_dir)
    elif config is None:
        cfg.project.dir = str(config_path.parent)
    if manifest is not None:
        cfg.project.manifest = str(manifest)

    try:
        ctx = build_context(cfg)
    except ManifestError as exc:
        err_console.print(f"[red]error:[/] {exc}")
        raise typer.Exit(2) from exc

    result = run(cfg, ctx)
    if select is not None:
        result.violations = [v for v in result.violations if _select_match(select, v.path)]
    return cfg, ctx, result


@app.command()
def check(
    config: Annotated[
        Path | None, typer.Option("--config", "-c", help="Path to dbt_arch_unit.yaml.")
    ] = None,
    project_dir: Annotated[
        Path | None, typer.Option("--project-dir", help="Override project.dir.")
    ] = None,
    manifest: Annotated[
        Path | None, typer.Option("--manifest", help="Override project.manifest path.")
    ] = None,
    select: Annotated[
        str | None, typer.Option("--select", help="Only report violations under this path glob.")
    ] = None,
    as_json: Annotated[bool, typer.Option("--json", help="Emit JSON instead of a table.")] = False,
    html: Annotated[
        Path | None, typer.Option("--html", help="Also write an HTML report to this path.")
    ] = None,
    warn_only: Annotated[
        bool, typer.Option("--warn-only", help="Never exit non-zero (report only).")
    ] = False,
) -> None:
    """Check the dbt project against its configured architecture rules."""
    cfg, ctx, result = _load_and_run(config, project_dir, manifest, select)

    if as_json:
        console.print_json(render_json(result))
    else:
        render_table(result, console)

    if html is not None:
        html.write_text(render_html(result, ctx, cfg))
        console.print(f"[green]✓ wrote HTML report to {html}[/]")

    if result.has_errors and not warn_only:
        raise typer.Exit(1)


@app.command()
def report(
    output: Annotated[
        Path, typer.Option("--output", "-o", help="Path to write the HTML report.")
    ] = Path("dbt_arch_unit_report.html"),
    config: Annotated[
        Path | None, typer.Option("--config", "-c", help="Path to dbt_arch_unit.yaml.")
    ] = None,
    project_dir: Annotated[
        Path | None, typer.Option("--project-dir", help="Override project.dir.")
    ] = None,
    manifest: Annotated[
        Path | None, typer.Option("--manifest", help="Override project.manifest path.")
    ] = None,
    select: Annotated[
        str | None, typer.Option("--select", help="Only include violations under this path glob.")
    ] = None,
    open_browser: Annotated[
        bool, typer.Option("--open", help="Open the report in a browser when done.")
    ] = False,
    warn_only: Annotated[
        bool, typer.Option("--warn-only", help="Never exit non-zero (report only).")
    ] = False,
) -> None:
    """Run the checks and write a full HTML report (issues, percentages, charts)."""
    cfg, ctx, result = _load_and_run(config, project_dir, manifest, select)
    output.write_text(render_html(result, ctx, cfg))
    console.print(f"[green]✓ wrote HTML report to {output}[/]")
    console.print(
        f"  {len(result.errors)} error(s), {len(result.warnings)} warning(s) "
        f"across {len(ctx.models)} models"
    )
    if open_browser:
        import webbrowser

        webbrowser.open(output.resolve().as_uri())

    if result.has_errors and not warn_only:
        raise typer.Exit(1)


def _select_match(pattern: str, path: str) -> bool:
    from dbt_arch_unit.context import _glob_to_regex

    return bool(_glob_to_regex(pattern).match(path))


@app.command("list-rules")
def list_rules(
    category: Annotated[str | None, typer.Option("--category", help="Filter by category.")] = None,
) -> None:
    """List every available rule."""
    table = Table(header_style="bold")
    table.add_column("rule", style="cyan")
    table.add_column("category", style="magenta")
    table.add_column("source", style="dim")
    table.add_column("description")
    for meta in all_rules():
        if category and meta.category != category:
            continue
        table.add_row(meta.name, meta.category, meta.source, meta.description)
    console.print(table)


@app.command()
def explain(rule: str) -> None:
    """Explain a single rule: what it checks and its config keys."""
    try:
        meta, _ = get_rule(rule)
    except KeyError:
        err_console.print(f"[red]error:[/] unknown rule '{rule}'")
        raise typer.Exit(2) from None
    console.print(f"[bold cyan]{meta.name}[/]  [magenta]({meta.category})[/]")
    console.print(f"[dim]category: {meta.category} · source: {meta.source}[/]")
    console.print(f"\n{meta.description}\n")
    if meta.config_keys:
        console.print("[bold]config:[/]")
        for key, desc in meta.config_keys.items():
            console.print(f"  [green]{key}[/]: {desc}")
    else:
        console.print("[dim]no configuration options[/]")


@app.command()
def init(
    project_dir: Annotated[
        Path, typer.Option("--project-dir", help="The dbt project directory to inspect.")
    ] = Path("."),
    path: Annotated[Path | None, typer.Option("--path", help="Where to write the config.")] = None,
    force: Annotated[bool, typer.Option("--force", help="Overwrite an existing config.")] = False,
) -> None:
    """Verify this is a dbt project, then scaffold a tailored dbt_arch_unit.yaml."""
    inspection = inspect_dbt_project(project_dir)

    console.print(f"[bold]Inspecting dbt project at[/] {inspection.project_dir}")
    for check in inspection.checks:
        mark = "[green]✓[/]" if check.ok else ("[red]✗[/]" if check.required else "[yellow]•[/]")
        detail = f" [dim]— {check.detail}[/]" if check.detail else ""
        console.print(f"  {mark} {check.name}{detail}")

    if not inspection.is_dbt_project:
        err_console.print(
            "\n[red]error:[/] this does not look like a dbt project — no config was created."
        )
        raise typer.Exit(1)

    target = path or inspection.project_dir / CONFIG_FILENAME
    if target.exists() and not force:
        err_console.print(f"\n[yellow]{target} already exists — use --force to overwrite.[/]")
        raise typer.Exit(1)

    model_path = inspection.model_paths[0] if inspection.model_paths else "models"
    content = render_config(model_path, inspection.detected_layers)
    target.write_text(content)

    if inspection.detected_layers:
        layers = ", ".join(inspection.detected_layers)
        console.print(f"\n[green]✓ wrote {target}[/] [dim](detected layers: {layers})[/]")
    else:
        console.print(f"\n[green]✓ wrote {target}[/] [dim](used default layers)[/]")
    console.print("  Next: run [cyan]dbt parse[/] then [cyan]dbt-arch-unit check[/].")


@app.command()
def version() -> None:
    """Print the version."""
    console.print(__version__)


if __name__ == "__main__":
    app()
