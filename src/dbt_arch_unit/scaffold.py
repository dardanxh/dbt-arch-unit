"""dbt-project detection and config scaffolding for `init`.

`inspect_dbt_project` decides whether a directory looks like a dbt project (and
why not). `render_config` builds a commented dbt_arch_unit.yaml, tailored to the
layer folders it finds.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

# Folder name (lowercased) -> conventional model-name prefixes for that layer.
KNOWN_LAYERS: dict[str, list[str]] = {
    "staging": ["stg_"],
    "stg": ["stg_"],
    "intermediate": ["int_"],
    "int": ["int_"],
    "marts": ["fct_", "dim_"],
    "mart": ["fct_", "dim_"],
    "core": ["fct_", "dim_"],
    "reporting": ["rpt_"],
    "reports": ["rpt_"],
    "report": ["rpt_"],
}

_DEFAULT_LAYERS: dict[str, list[str]] = {
    "staging": ["stg_"],
    "intermediate": ["int_"],
    "marts": ["fct_", "dim_"],
    "reporting": ["rpt_"],
}


@dataclass
class Check:
    name: str
    ok: bool
    required: bool
    detail: str = ""


@dataclass
class Inspection:
    project_dir: Path
    checks: list[Check] = field(default_factory=list)
    model_paths: list[str] = field(default_factory=lambda: ["models"])
    detected_layers: dict[str, list[str]] = field(default_factory=dict)

    @property
    def is_dbt_project(self) -> bool:
        return all(c.ok for c in self.checks if c.required)


def _find_dbt_project_file(project_dir: Path) -> Path | None:
    for name in ("dbt_project.yml", "dbt_project.yaml"):
        candidate = project_dir / name
        if candidate.exists():
            return candidate
    return None


def inspect_dbt_project(project_dir: Path) -> Inspection:
    project_dir = project_dir.resolve()
    inspection = Inspection(project_dir=project_dir)

    project_file = _find_dbt_project_file(project_dir)
    inspection.checks.append(
        Check(
            "dbt_project.yml present",
            ok=project_file is not None,
            required=True,
            detail=str(project_file.name) if project_file else "not found in this directory",
        )
    )
    if project_file is None:
        return inspection

    try:
        project = yaml.safe_load(project_file.read_text()) or {}
    except yaml.YAMLError as exc:
        inspection.checks.append(
            Check("dbt_project.yml parses", ok=False, required=True, detail=str(exc))
        )
        return inspection

    inspection.checks.append(Check("dbt_project.yml parses", ok=True, required=True, detail=""))
    name = project.get("name")
    inspection.checks.append(
        Check(
            "project has a name",
            ok=bool(name),
            required=True,
            detail=f"name: {name}" if name else "missing top-level 'name'",
        )
    )

    model_paths = project.get("model-paths") or ["models"]
    inspection.model_paths = list(model_paths)
    existing = [p for p in model_paths if (project_dir / p).is_dir()]
    inspection.checks.append(
        Check(
            "models directory exists",
            ok=bool(existing),
            required=True,
            detail=", ".join(existing) if existing else f"none of {model_paths} found",
        )
    )

    sql_files = [f for p in existing for f in (project_dir / p).rglob("*.sql")]
    inspection.checks.append(
        Check(
            "contains model files",
            ok=bool(sql_files),
            required=False,
            detail=f"{len(sql_files)} .sql model(s)" if sql_files else "no .sql files yet",
        )
    )

    manifest = project_dir / "target" / "manifest.json"
    manifest_detail = (
        "target/manifest.json" if manifest.exists() else "run `dbt parse` before `check`"
    )
    inspection.checks.append(
        Check(
            "compiled manifest present",
            ok=manifest.exists(),
            required=False,
            detail=manifest_detail,
        )
    )

    inspection.detected_layers = _detect_layers(project_dir, existing)
    return inspection


def _detect_layers(project_dir: Path, model_paths: list[str]) -> dict[str, list[str]]:
    detected: dict[str, list[str]] = {}
    for mp in model_paths:
        base = project_dir / mp
        if not base.is_dir():
            continue
        for sub in sorted(p for p in base.iterdir() if p.is_dir()):
            prefixes = KNOWN_LAYERS.get(sub.name.lower())
            if prefixes is not None and sub.name not in detected:
                detected[sub.name] = prefixes
    return detected


def render_config(model_path: str, layers: dict[str, list[str]]) -> str:
    """Render a commented dbt_arch_unit.yaml for the given layers."""
    layers = layers or _DEFAULT_LAYERS
    layer_lines = []
    for name, prefixes in layers.items():
        prefix_str = ", ".join(f'"{p}"' for p in prefixes)
        layer_lines.append(
            f'  {name}: {{ paths: ["{model_path}/{name}/**"], prefixes: [{prefix_str}] }}'
        )
    layer_block = "\n".join(layer_lines)
    return _HEADER.format(model_path=model_path, layers=layer_block) + _RULES


_HEADER = """# dbt_arch_unit.yaml — architectural rules for this dbt project.
# Generated by `dbt-arch-unit init`. Run `dbt parse` first, then `dbt-arch-unit check`.
version: 1

project:
  dir: "."
  manifest: "target/manifest.json"
  models_path: "{model_path}"

# Layer definitions, detected from your models/ folders. Adjust as needed.
layers:
{layers}

defaults:
  severity: error
  include: ["{model_path}/**"]
  exclude: []
"""

_RULES = """
rules:
  # --- Layering & dependencies ---------------------------------------------
  - name: layer-dependencies
    config:
      allow:
        staging:      [source]
        intermediate: [staging, intermediate]
        marts:        [staging, intermediate, marts]
        reporting:    [marts]
  - name: sources-only-in-staging
  - name: staging-one-source
  - name: no-orphan-models
    severity: warning

  # --- Naming ---------------------------------------------------------------
  - name: layer-name-prefix
  - name: directory-prefix-match
  - name: model-name-regex
    config:
      forbid: ["tmp", "temp", "copy", "final", "test"]

  # --- Testing & documentation ---------------------------------------------
  - name: require-primary-key
    include: ["**/marts/**"]
  - name: source-freshness
    severity: warning
  - name: model-has-description

  # --- Style & complexity ---------------------------------------------------
  - name: max-lines-of-code
    config: { max: 200, ignore_comments: true }
  - name: no-select-star
    exclude: ["**/staging/**"]
  - name: max-joins
    config: { max: 7 }
  - name: require-ref-not-hardcoded

  # --- Materialization governance ------------------------------------------
  - name: incremental-requires-keys
"""
