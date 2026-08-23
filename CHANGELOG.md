# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-08-23

### Added
- Initial release of **dbt-arch-unit** — architectural unit testing for dbt.
- Declarative `dbt_arch_unit.yaml` contract with reusable `layers`, per-rule
  `severity`, and `include`/`exclude`/`layers`/`tags` selectors.
- Hybrid parsing: `target/manifest.json` for the dependency graph, configs, tags,
  columns and tests; raw `.sql` files for LOC, CTEs, `select *`, joins.
- **38 rules** across six categories: dependencies, naming, testing,
  documentation, style, and materialization governance.
- CLI (Typer + Rich):
  - `check` — run configured rules; `--json`, `--select`, `--html`, `--warn-only`.
  - `report` — write a self-contained HTML report (issues, percentages, charts).
  - `list-rules` / `explain` — browse the rule catalog.
  - `init` — validate the directory is a dbt project, then scaffold a config
    tailored to the detected `models/` layer folders.
- Pre-commit hook definition (`.pre-commit-hooks.yaml`) for downstream dbt repos.

[Unreleased]: https://github.com/dardanxh/dbt-arch-unit/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/dardanxh/dbt-arch-unit/releases/tag/v0.1.0
