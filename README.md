# dbt-arch-unit

[![CI](https://github.com/dardanxh/dbt-arch-unit/actions/workflows/ci.yml/badge.svg)](https://github.com/dardanxh/dbt-arch-unit/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![PyPI](https://img.shields.io/pypi/v/dbt-arch-unit.svg)](https://pypi.org/project/dbt-arch-unit/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

**Architectural unit testing for dbt projects.**

Like [ArchUnit](https://www.archunit.org/) for Java or
[import-linter](https://github.com/seddonym/import-linter) for Python — but for
dbt. Declare the architecture your team already agreed on in a single
`dbt_arch_unit.yaml`, and enforce it in CI and pre-commit.

```yaml
# dbt_arch_unit.yaml  (next to dbt_project.yml)
layers:
  staging:   { paths: ["models/staging/**"],   prefixes: ["stg_"] }
  marts:     { paths: ["models/marts/**"],      prefixes: ["fct_", "dim_"] }
  reporting: { paths: ["models/reporting/**"],  prefixes: ["rpt_"] }

rules:
  - name: layer-dependencies
    config:
      allow:
        staging:   [source]
        marts:     [staging, marts]
        reporting: [marts]
  - name: max-lines-of-code
    config: { max: 200 }
  - name: require-primary-key
    include: ["models/marts/**"]
```

```bash
# after `dbt parse` (produces target/manifest.json)
dbt-arch-unit check          # run all configured rules, exit 1 on violations
dbt-arch-unit check --json   # machine-readable output for CI
dbt-arch-unit report -o report.html --open   # full HTML report + open it
dbt-arch-unit list-rules     # every available rule
dbt-arch-unit explain layer-dependencies
dbt-arch-unit init           # validate this is a dbt project, then scaffold config
```

## Installation

Requires Python 3.10+.

```bash
# once published to PyPI:
pip install dbt-arch-unit
pipx install dbt-arch-unit          # isolated CLI install
uv tool install dbt-arch-unit       # via uv

# from source (available today):
uv tool install git+https://github.com/dardanxh/dbt-arch-unit
pipx install git+https://github.com/dardanxh/dbt-arch-unit

# for local development:
git clone https://github.com/dardanxh/dbt-arch-unit
cd dbt-arch-unit
uv sync --extra dev
uv run dbt-arch-unit --help
```

### Use as a pre-commit hook

Add to your dbt project's `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/dardanxh/dbt-arch-unit
    rev: v0.1.0
    hooks:
      - id: dbt-arch-unit
```

## How it works

Hybrid parsing: `target/manifest.json` supplies the accurate dependency graph,
configs, tags, columns and tests; raw `.sql`/`.yml` files supply line counts, CTE
structure, `select *` usage and joins. Each rule is a small, self-contained
function. See `dbt-arch-unit list-rules` for the full catalog.

## `init` — guarded scaffolding

`dbt-arch-unit init` first checks that the target directory is actually a dbt
project before writing anything:

- `dbt_project.yml` exists and parses, and declares a `name` (required),
- the `model-paths` directory exists (required),
- it contains `.sql` models and a compiled `target/manifest.json` (advisory).

If the required checks fail, **no file is written** and it exits non-zero. On
success it auto-detects your `models/` layer folders (staging, intermediate,
marts, reporting, …) and writes a `dbt_arch_unit.yaml` tailored to them.

```bash
dbt-arch-unit init                          # inspect ./ and scaffold
dbt-arch-unit init --project-dir path/to/dbt
dbt-arch-unit init --force                  # overwrite an existing config
```

## HTML report

`dbt-arch-unit report` runs the checks and writes a single, self-contained
`.html` file (no external assets) with:

- a pass/fail banner and headline stats (total issues, errors, warnings),
- **percentages** — % of models affected and % of rules passing,
- bar-chart breakdowns of issues **by category, by rule, and by severity**,
- the full findings table (severity, rule, location, message).

```bash
dbt-arch-unit report -o architecture_report.html          # write the report
dbt-arch-unit report -o report.html --open                # and open it
dbt-arch-unit check --html report.html                    # table + report in one go
```

## Rule catalog

**38 rules** across six categories — dependencies, naming, testing,
documentation, style, and materialization governance. Run `dbt-arch-unit
list-rules` to see them all, or `dbt-arch-unit explain <rule>` for details and
config keys.

## Contributing

Contributions are very welcome — especially new rules. See
[CONTRIBUTING.md](CONTRIBUTING.md) for the dev setup and a walkthrough of adding
a rule, and please follow the [Code of Conduct](CODE_OF_CONDUCT.md).

## License

[MIT](LICENSE) © Dardan Xhymshiti
