"""dbt-project detection and config scaffolding for `init`.

`inspect_dbt_project` decides whether a directory looks like a dbt project (and
why not). `render_config` builds a commented dbt_arch.yaml, tailored to the
layer folders it finds.
"""

from __future__ import annotations

import re
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
    """Render a commented dbt_arch.yaml for the given layers.

    Enables a few high-signal rules and lists every other available rule
    commented-out with its options, so users can enable them selectively.
    """
    layers = layers or _DEFAULT_LAYERS
    layer_lines = []
    for name, prefixes in layers.items():
        prefix_str = ", ".join(f'"{p}"' for p in prefixes)
        layer_lines.append(
            f'  {name}: {{ paths: ["{model_path}/{name}/**"], prefixes: [{prefix_str}] }}'
        )
    layer_block = "\n".join(layer_lines)
    chain = "source > " + " > ".join(layers)

    # Emit only what isn't already the default: version (=1), project (dir/manifest/
    # models_path) and defaults (severity/include/exclude) are all left implicit.
    sections = [_HEADER_COMMENT]
    if model_path != "models":
        sections.append(f'project:\n  models_path: "{model_path}"')
    sections.append(
        "# Layer definitions, detected from your models/ folders. Adjust as needed.\n"
        f"layers:\n{layer_block}"
    )
    if model_path != "models":
        sections.append(f'defaults:\n  include: ["{model_path}/**"]')
    return "\n\n".join(sections) + "\n" + _render_rules(chain)


# The few rules `init` enables by default — high-signal and low-config.
# Value = YAML body lines placed under the rule's `- name:` item ({chain} is filled in).
_ACTIVE_RULES: dict[str, list[str]] = {
    "expect-dependencies": ['allow: ["{chain}"]', "deny: []"],
    "expect-layer-name-prefix": [],
    "expect-model-name-convention": ["case: snake_case"],
    "expect-min-tests-per-model": ["min: 1", "severity: warning"],
    "expect-model-has-description": ["severity: warning"],
    "expect-no-select-star": [],
}

_CATEGORY_ORDER = ["dependencies", "naming", "materialization", "testing", "documentation", "style"]
_CATEGORY_TITLES = {
    "dependencies": "Layering & dependencies",
    "naming": "Naming",
    "materialization": "Materialization & config governance",
    "testing": "Testing & quality gates",
    "documentation": "Documentation",
    "style": "Style & complexity",
}


def _default_value(desc: str) -> str | None:
    """Pull an example value out of a config-key description mentioning a default."""
    match = re.search(r"default:\s*([^)]+?)\s*\)", desc) or re.search(r"default:\s*(.+)$", desc)
    if not match:
        return None
    raw = match.group(1).strip().rstrip(".")
    if raw.isdigit() or raw in ("true", "false"):
        return raw
    if "," in raw:  # a list, e.g. "unique_key, on_schema_change"
        return "[" + ", ".join(x.strip() for x in raw.split(",")) + "]"
    return raw


def _render_rules(chain: str) -> str:
    from dbt_arch_unit.rules import RuleMeta, all_rules

    by_cat: dict[str, list[RuleMeta]] = {}
    for meta in all_rules():
        by_cat.setdefault(meta.category, []).append(meta)

    out = ["", "rules:"]
    for cat in _CATEGORY_ORDER:
        metas = by_cat.get(cat)
        if not metas:
            continue
        title = _CATEGORY_TITLES.get(cat, cat)
        out.append(f"  # === {title} " + "=" * max(3, 60 - len(title)))
        for meta in metas:
            out.append(f"  # {meta.description}")
            if meta.name in _ACTIVE_RULES:
                out.append(f"  - name: {meta.name}")
                for line in _ACTIVE_RULES[meta.name]:
                    out.append("    " + line.replace("{chain}", chain))
            else:
                out.append(f"  # - name: {meta.name}")
                for key, kdesc in meta.config_keys.items():
                    value = _default_value(kdesc)
                    note = re.sub(r"\s*\(?default:[^)]*\)?", "", kdesc).strip()
                    comment = f"   # {note}" if note else ""
                    out.append(f"  #     {key}: {value if value is not None else '...'}{comment}")
        out.append("")
    return "\n".join(out).rstrip() + "\n"


_HEADER_COMMENT = """# dbt_arch.yaml — architectural rules for this dbt project.
# Generated by `dbt-arch-unit init`. Run `dbt parse` first, then `dbt-arch-unit check`.
#
# A few high-signal rules are enabled below; every other available rule is listed
# commented-out with its options — uncomment and tune to enable.
# severity defaults to `error` (fails CI); set `severity: warning` to report-only.
# Scope any rule with `scope: [layers]` / `ignore: [layers]`."""
