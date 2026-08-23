# CHANGELOG

All notable changes to this project are documented here. This file is generated
automatically by [python-semantic-release](https://python-semantic-release.readthedocs.io)
from [Conventional Commits](https://www.conventionalcommits.org) — do not edit by hand.

<!-- version list -->

## v0.1.0 (2026-08-23)

### Continuous Integration

- Automate versioning and releases with python-semantic-release
  ([`9900087`](https://github.com/dardanxh/dbt-arch-unit/commit/9900087e648e40850b7f48e41a5fc5c8296f8ad1))

Version, git tag, GitHub Release and CHANGELOG are now derived from Conventional Commit messages.
  The release workflow runs PSR on pushes to main; PyPI publishing is gated behind the PYPI_PUBLISH
  repo variable.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>

### Features

- Dbt-arch-unit — architectural unit testing for dbt
  ([`9407556`](https://github.com/dardanxh/dbt-arch-unit/commit/9407556e51dad87e50c12add5f43e0a5e2c6582a))

Enforce a team's dbt conventions (layering, naming, testing, docs, style, materialization) via a
  declarative dbt_arch_unit.yaml. Ships 38 rules, a Typer+Rich CLI
  (check/report/list-rules/explain/init), a self-contained HTML report, and a pre-commit hook.
  Includes CI, release automation, and full OSS governance files.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
