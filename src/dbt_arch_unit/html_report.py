"""Self-contained HTML report of a run's findings.

No external assets or JavaScript — the produced file is a single portable .html
suitable for CI artifacts. Includes a summary, percentage breakdowns and the full
list of violations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from html import escape

from dbt_arch_unit.config import ArchUnitConfig
from dbt_arch_unit.context import ProjectContext
from dbt_arch_unit.rules import _REGISTRY
from dbt_arch_unit.runner import RunResult
from dbt_arch_unit.violation import Severity


@dataclass
class ReportMetrics:
    total_violations: int = 0
    errors: int = 0
    warnings: int = 0
    models_total: int = 0
    models_affected: int = 0
    rules_evaluated: int = 0
    rules_triggered: int = 0
    by_severity: dict[str, int] = field(default_factory=dict)
    by_category: dict[str, int] = field(default_factory=dict)
    by_rule: dict[str, int] = field(default_factory=dict)

    @property
    def pct_models_affected(self) -> float:
        return 100 * self.models_affected / self.models_total if self.models_total else 0.0

    @property
    def pct_rules_passed(self) -> float:
        if not self.rules_evaluated:
            return 100.0
        return 100 * (self.rules_evaluated - self.rules_triggered) / self.rules_evaluated

    @property
    def passed(self) -> bool:
        return self.errors == 0


def _category_of(rule_name: str) -> str:
    entry = _REGISTRY.get(rule_name)
    return entry[0].category if entry else "unknown"


def build_metrics(result: RunResult, ctx: ProjectContext, config: ArchUnitConfig) -> ReportMetrics:
    m = ReportMetrics()
    m.total_violations = len(result.violations)
    m.errors = len(result.errors)
    m.warnings = len(result.warnings)
    m.models_total = len(ctx.models)
    model_ids = {n.unique_id for n in ctx.models}
    m.models_affected = len({v.node for v in result.violations if v.node in model_ids})

    configured = {r.name for r in config.rules}
    m.rules_evaluated = len(configured) - len(set(result.unknown_rules))
    m.rules_triggered = len({v.rule for v in result.violations})

    for v in result.violations:
        m.by_severity[v.severity.value] = m.by_severity.get(v.severity.value, 0) + 1
        cat = _category_of(v.rule)
        m.by_category[cat] = m.by_category.get(cat, 0) + 1
        m.by_rule[v.rule] = m.by_rule.get(v.rule, 0) + 1
    return m


def _bar_rows(counts: dict[str, int], total: int) -> str:
    if not counts:
        return '<tr><td colspan="3" class="muted">none</td></tr>'
    rows = []
    for label, count in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
        pct = 100 * count / total if total else 0
        rows.append(
            f'<tr><td class="label">{escape(label)}</td>'
            f'<td class="barcell"><div class="bar" style="width:{pct:.1f}%"></div></td>'
            f'<td class="num">{count} ({pct:.0f}%)</td></tr>'
        )
    return "\n".join(rows)


def _violation_rows(result: RunResult) -> str:
    if not result.violations:
        return '<tr><td colspan="4" class="muted">No violations 🎉</td></tr>'
    rows = []
    for v in sorted(result.violations, key=lambda x: (x.severity.value, x.rule, x.node)):
        sev_class = "err" if v.severity is Severity.ERROR else "warn"
        location = escape(f"{v.path}:{v.line}" if v.line else (v.path or v.node))
        rows.append(
            f"<tr>"
            f'<td><span class="pill {sev_class}">{v.severity.value}</span></td>'
            f'<td class="mono">{escape(v.rule)}</td>'
            f'<td class="mono muted">{location}</td>'
            f"<td>{escape(v.message)}</td>"
            f"</tr>"
        )
    return "\n".join(rows)


def _stat(label: str, value: str, tone: str = "") -> str:
    return (
        f'<div class="stat {tone}"><div class="stat-value">{escape(value)}</div>'
        f'<div class="stat-label">{escape(label)}</div></div>'
    )


def render_html(
    result: RunResult,
    ctx: ProjectContext,
    config: ArchUnitConfig,
    generated_at: datetime | None = None,
) -> str:
    m = build_metrics(result, ctx, config)
    when = (generated_at or datetime.now()).strftime("%Y-%m-%d %H:%M:%S")
    project = escape(str(ctx.manifest.metadata.get("project_name", "dbt project")))
    status = "PASSED" if m.passed else "FAILED"
    status_tone = "ok" if m.passed else "bad"

    stats = "".join(
        [
            _stat("Status", status, status_tone),
            _stat("Total issues", str(m.total_violations)),
            _stat("Errors", str(m.errors), "bad" if m.errors else ""),
            _stat("Warnings", str(m.warnings), "warntone" if m.warnings else ""),
            _stat("Models affected", f"{m.models_affected}/{m.models_total}"),
            _stat("% models affected", f"{m.pct_models_affected:.0f}%"),
            _stat("Rules evaluated", str(m.rules_evaluated)),
            _stat("% rules passing", f"{m.pct_rules_passed:.0f}%"),
        ]
    )

    return _TEMPLATE.format(
        project=project,
        when=when,
        status=status,
        status_tone=status_tone,
        stats=stats,
        by_category=_bar_rows(m.by_category, m.total_violations),
        by_rule=_bar_rows(m.by_rule, m.total_violations),
        by_severity=_bar_rows(m.by_severity, m.total_violations),
        violations=_violation_rows(result),
        year=when[:4],
    )


_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>dbt-arch-unit report — {project}</title>
<style>
  :root {{ --err:#d64545; --warn:#c9820a; --ok:#2f9e44; --bar:#4c6ef5; --bg:#f6f7f9;
           --card:#fff; --line:#e4e7eb; --ink:#1f2933; --muted:#7b8794; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; font:14px/1.5 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;
          color:var(--ink); background:var(--bg); }}
  .wrap {{ max-width:1040px; margin:0 auto; padding:32px 20px 64px; }}
  header {{ display:flex; align-items:baseline; justify-content:space-between; flex-wrap:wrap; gap:8px; }}
  h1 {{ font-size:20px; margin:0; }}
  h2 {{ font-size:15px; text-transform:uppercase; letter-spacing:.05em; color:var(--muted);
        margin:32px 0 12px; }}
  .sub {{ color:var(--muted); }}
  .banner {{ margin-top:16px; padding:12px 16px; border-radius:8px; font-weight:600; }}
  .banner.ok {{ background:#e7f6ec; color:var(--ok); }}
  .banner.bad {{ background:#fbe9e9; color:var(--err); }}
  .stats {{ display:grid; grid-template-columns:repeat(4,1fr); gap:12px; margin-top:16px; }}
  .stat {{ background:var(--card); border:1px solid var(--line); border-radius:10px; padding:14px; }}
  .stat-value {{ font-size:22px; font-weight:700; }}
  .stat-label {{ color:var(--muted); font-size:12px; margin-top:2px; }}
  .stat.bad .stat-value {{ color:var(--err); }}
  .stat.ok .stat-value {{ color:var(--ok); }}
  .stat.warntone .stat-value {{ color:var(--warn); }}
  table {{ width:100%; border-collapse:collapse; background:var(--card);
           border:1px solid var(--line); border-radius:10px; overflow:hidden; }}
  th,td {{ text-align:left; padding:9px 12px; border-bottom:1px solid var(--line); vertical-align:top; }}
  th {{ background:#fafbfc; font-size:12px; text-transform:uppercase; letter-spacing:.04em;
        color:var(--muted); }}
  tr:last-child td {{ border-bottom:none; }}
  .label {{ width:200px; }}
  .num {{ width:110px; text-align:right; color:var(--muted); white-space:nowrap; }}
  .barcell {{ padding-right:0; }}
  .bar {{ height:12px; background:var(--bar); border-radius:6px; min-width:2px; }}
  .mono {{ font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:12.5px; }}
  .muted {{ color:var(--muted); }}
  .pill {{ display:inline-block; padding:1px 8px; border-radius:999px; font-size:11px;
           font-weight:700; text-transform:uppercase; }}
  .pill.err {{ background:#fbe9e9; color:var(--err); }}
  .pill.warn {{ background:#fdf3e0; color:var(--warn); }}
  footer {{ margin-top:40px; color:var(--muted); font-size:12px; text-align:center; }}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>dbt-arch-unit report</h1>
    <div class="sub">{project} · generated {when}</div>
  </header>
  <div class="banner {status_tone}">Architecture check {status}</div>

  <div class="stats">{stats}</div>

  <h2>Issues by category</h2>
  <table><tbody>{by_category}</tbody></table>

  <h2>Issues by rule</h2>
  <table><tbody>{by_rule}</tbody></table>

  <h2>Issues by severity</h2>
  <table><tbody>{by_severity}</tbody></table>

  <h2>All findings</h2>
  <table>
    <thead><tr><th>Severity</th><th>Rule</th><th>Location</th><th>Message</th></tr></thead>
    <tbody>{violations}</tbody>
  </table>

  <footer>Generated by dbt-arch-unit · {year}</footer>
</div>
</body>
</html>
"""
