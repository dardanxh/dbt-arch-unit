from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from dbt_arch_unit.cli import app

runner = CliRunner()
FIXTURE = Path(__file__).parent / "fixtures" / "demo_project"
CONFIG = FIXTURE / "dbt_arch.yaml"


def test_check_reports_errors_and_exits_nonzero():
    result = runner.invoke(app, ["check", "--config", str(CONFIG), "--project-dir", str(FIXTURE)])
    assert result.exit_code == 1
    assert "error" in result.stdout.lower()


def test_check_json_output():
    result = runner.invoke(
        app, ["check", "--config", str(CONFIG), "--project-dir", str(FIXTURE), "--json"]
    )
    payload = json.loads(result.stdout)
    assert payload["summary"]["errors"] > 0
    assert any(v["rule"] == "expect-no-select-star" for v in payload["violations"])


def test_check_warn_only_exits_zero():
    result = runner.invoke(
        app, ["check", "--config", str(CONFIG), "--project-dir", str(FIXTURE), "--warn-only"]
    )
    assert result.exit_code == 0


def test_list_rules():
    result = runner.invoke(app, ["list-rules"])
    assert result.exit_code == 0
    assert "expect-dependencies" in result.stdout


def test_explain():
    result = runner.invoke(app, ["explain", "expect-max-lines-of-code"])
    assert result.exit_code == 0
    assert "max" in result.stdout


def test_init_writes_config_for_dbt_project(tmp_path):
    target = tmp_path / "dbt_arch.yaml"
    result = runner.invoke(app, ["init", "--project-dir", str(FIXTURE), "--path", str(target)])
    assert result.exit_code == 0
    assert target.exists()
    text = target.read_text()
    assert "expect-dependencies" in text
    # layers auto-detected from the fixture's models/ subfolders
    assert "staging:" in text and "marts:" in text


def test_init_rejects_non_dbt_project(tmp_path):
    result = runner.invoke(app, ["init", "--project-dir", str(tmp_path)])
    assert result.exit_code == 1
    # the required dbt_project.yml check is shown as failed, and no config is written
    assert "dbt_project.yml present" in result.stdout
    assert not (tmp_path / "dbt_arch.yaml").exists()
