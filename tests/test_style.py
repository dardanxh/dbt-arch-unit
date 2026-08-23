from __future__ import annotations

M = "model.demo."


def test_no_select_star(run):
    got = run("no-select-star", exclude=["models/staging/**"])
    assert got == {M + "fct_orders"}


def test_max_joins(run):
    assert run("max-joins", config={"max": 7}) == {M + "fct_orders"}


def test_require_ref_not_hardcoded(run):
    assert run("require-ref-not-hardcoded") == {M + "fct_orders"}


def test_max_ctes(run):
    got = run("max-ctes", include=["models/staging/**"], config={"max": 1})
    assert got == {M + "stg_customers"}


def test_require_import_cte_structure(run):
    assert M + "fct_orders" in run("require-import-cte-structure")
