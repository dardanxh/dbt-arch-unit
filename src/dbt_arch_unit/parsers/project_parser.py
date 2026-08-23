"""Filesystem-level reads: dbt_project.yml and a node's raw .sql on disk."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def load_dbt_project(project_dir: Path) -> dict[str, Any]:
    """Read dbt_project.yml if present (used for defaults like target schema)."""
    path = project_dir / "dbt_project.yml"
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text()) or {}


def read_model_source(project_dir: Path, original_file_path: str, fallback: str = "") -> str:
    """Read a model's raw SQL from disk, falling back to the manifest's copy."""
    if original_file_path:
        candidate = project_dir / original_file_path
        if candidate.exists():
            return candidate.read_text()
    return fallback
