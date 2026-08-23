"""Load and validate a dbt manifest.json into typed models."""

from __future__ import annotations

import json
from pathlib import Path

from dbt_arch_unit.models.manifest import Manifest


class ManifestError(Exception):
    """Raised when the manifest is missing or cannot be parsed."""


def load_manifest(path: Path) -> Manifest:
    if not path.exists():
        raise ManifestError(
            f"manifest not found at '{path}'. Run `dbt parse` (or `dbt compile`) first."
        )
    try:
        raw = json.loads(path.read_text())
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive
        raise ManifestError(f"could not parse manifest at '{path}': {exc}") from exc
    return Manifest.model_validate(raw)
