# CHANGELOG

All notable changes to this project are documented here. This file is generated
automatically by [python-semantic-release](https://python-semantic-release.readthedocs.io)
from [Conventional Commits](https://www.conventionalcommits.org) — do not edit by hand.

<!-- version list -->

## v1.0.0 (2026-08-25)

### Features

- Overhaul rules & config — expect-* naming, layer scoping, new checks, leaner init
  ([`236f5e6`](https://github.com/dardanxh/dbt-arch-unit/commit/236f5e6bdfaf284aa7b620df5d1efe7f7ea7879c))

- Replace layer-dependencies map with arrow-chain test-dependencies rule
  ([`ff30a26`](https://github.com/dardanxh/dbt-arch-unit/commit/ff30a260700d2dffe568273a907585db9409a3b4))


## v0.1.2 (2026-08-25)

### Bug Fixes

- Lower minimum Python to 3.10 for broader compatibility
  ([`511f721`](https://github.com/dardanxh/dbt-arch-unit/commit/511f721c296c58e7277721b19ccbff0a411f97a7))

### Continuous Integration

- Run semantic-release directly with pinned gitpython<3.1.45
  ([`54336fa`](https://github.com/dardanxh/dbt-arch-unit/commit/54336fa8ead298cca67220bed5b84e3a466bfef4))


## v0.1.1 (2026-08-23)

### Bug Fixes

- Ship py.typed marker for PEP 561 type support
  ([`6d9635d`](https://github.com/dardanxh/dbt-arch-unit/commit/6d9635dba8d9cb7885e33f54de1072b5bd5e3ae5))

The package declares "Typing :: Typed" but shipped no py.typed marker, so downstream type checkers
  ignored dbt-arch-unit's inline types. Add the marker so consumers pick up the annotations.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>


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
