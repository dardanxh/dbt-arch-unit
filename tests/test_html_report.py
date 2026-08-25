from __future__ import annotations

from datetime import datetime
from pathlib import Path

from typer.testing import CliRunner

from dbt_arch_unit.cli import app
from dbt_arch_unit.config import load_config
from dbt_arch_unit.context import ProjectContext
from dbt_arch_unit.html_report import build_metrics, render_html
from dbt_arch_unit.parsers.manifest_parser import load_manifest
from dbt_arch_unit.runner import run

runner = CliRunner()
FIXTURE = Path(__file__).parent / "fixtures" / "demo_project"
CONFIG = FIXTURE / "dbt_arch.yaml"


def _run():
    cfg = load_config(CONFIG)
    cfg.project.dir = str(FIXTURE)
    manifest = load_manifest(FIXTURE / "target" / "manifest.json")
    ctx = ProjectContext(cfg, manifest)
    return cfg, ctx, run(cfg, ctx)


def test_build_metrics():
    cfg, ctx, result = _run()
    m = build_metrics(result, ctx, cfg)
    assert m.errors > 0
    assert m.models_total == len(ctx.models)
    assert 0 < m.models_affected <= m.models_total
    assert m.by_category["style"] >= 1
    assert 0 <= m.pct_rules_passed <= 100
    assert m.passed is False


def test_render_html_contains_sections():
    cfg, ctx, result = _run()
    html = render_html(result, ctx, cfg, generated_at=datetime(2026, 1, 1, 12, 0, 0))
    assert "<!doctype html>" in html
    assert "Architecture check FAILED" in html
    assert "Issues by category" in html
    assert "% models affected" in html
    assert "expect-no-select-star" in html
    assert "2026-01-01" in html


def test_report_command_writes_file(tmp_path):
    out = tmp_path / "report.html"
    result = runner.invoke(
        app,
        ["report", "-o", str(out), "--config", str(CONFIG), "--project-dir", str(FIXTURE)],
    )
    assert result.exit_code == 1  # errors present
    assert out.exists()
    assert "dbt-arch-unit report" in out.read_text()


def test_check_html_flag(tmp_path):
    out = tmp_path / "check.html"
    runner.invoke(
        app,
        [
            "check",
            "--config",
            str(CONFIG),
            "--project-dir",
            str(FIXTURE),
            "--html",
            str(out),
            "--warn-only",
        ],
    )
    assert out.exists()
