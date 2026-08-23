# Contributing to dbt-arch-unit

Thanks for your interest in improving **dbt-arch-unit**! This project turns a
team's dbt conventions into enforceable, testable rules. Contributions — new
rules, bug fixes, docs — are very welcome.

## Development setup

You need [uv](https://docs.astral.sh/uv/) and Python 3.13+.

```bash
git clone https://github.com/dardanxh/dbt-arch-unit
cd dbt-arch-unit
uv sync --extra dev          # install the package + dev tools
uv run dbt-arch-unit --help  # sanity check
```

## The checks CI runs (run them before opening a PR)

```bash
uv run ruff check            # lint
uv run ruff format --check   # formatting
uv run mypy src              # static types (strict)
uv run pytest                # tests
```

Optionally install the local git hooks so these run automatically:

```bash
uv run pre-commit install
```

## How the project is organised

```
src/dbt_arch_unit/
  models/manifest.py   # typed view of dbt's manifest.json
  parsers/             # manifest loader + raw-SQL fact extraction
  config.py            # the dbt_arch_unit.yaml contract (pydantic)
  context.py           # ProjectContext: layers, selectors, cached SQL, test indexes
  rules/               # one module per category, one function per rule
  runner.py reporting.py html_report.py cli.py scaffold.py
tests/                 # per-category tests + a demo project fixture
```

## Adding a new rule

Rules are small, self-contained functions registered by name. To add one:

1. **Write the function** in the right category module under `src/dbt_arch_unit/rules/`
   (`dependencies`, `naming`, `testing`, `documentation`, `style`, `materialization`).
   Use the `@register(...)` decorator and the `(ctx, rule)` signature:

   ```python
   @register(
       "no-select-star",
       "style",
       "Models must not use `select *` in their final projection.",
       source="file",  # "manifest" | "file" | "both"
       config_keys={"allow_in_ctes": "permit `select *` inside CTEs (default: true)"},
   )
   def no_select_star(ctx: ProjectContext, rule: RuleConfig) -> Iterable[Violation]:
       for model in ctx.models_for(rule):  # scoping is handled for you
           if ctx.sql(model).has_select_star(allow_in_ctes=rule.config.get("allow_in_ctes", True)):
               yield ctx.violation(rule, model, "uses `select *`")
   ```

   Let `ctx.models_for(rule)` do the include/exclude/layer/tag scoping — never
   re-implement it. Read manifest facts from `ctx`, and raw-SQL facts from
   `ctx.sql(model)`.

2. **Add a fixture case** if needed in `tests/fixtures/demo_project/` (the demo
   project is deliberately "bad" so rules have something to catch).

3. **Add a test** in the matching `tests/test_<category>.py` asserting exactly
   which nodes the rule flags.

4. **Document it** — it shows up automatically in `dbt-arch-unit list-rules` and
   `explain <rule>` from the `@register` metadata. Add it to `CHANGELOG.md`.

## Commit & PR conventions

- Keep PRs focused; one rule or fix per PR where possible.
- Use clear, imperative commit messages (Conventional Commits style appreciated,
  e.g. `feat(rules): add max-macro-depth`).
- Ensure `ruff`, `mypy`, and `pytest` all pass.
- Update `README.md` / `CHANGELOG.md` when behaviour or the rule catalog changes.

## Reporting bugs / proposing rules

Open an issue using the templates — there's a dedicated **"New rule proposal"**
template for suggesting architecture rules.

By contributing you agree that your contributions are licensed under the
project's [MIT License](LICENSE).
