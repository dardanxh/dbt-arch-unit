from __future__ import annotations

M = "model.demo."


def test_no_select_star(run):
    got = run("expect-no-select-star", exclude=["models/staging/**"])
    assert got == {M + "fct_orders"}


def test_max_joins(run):
    assert run("expect-max-joins", config={"max": 7}) == {M + "fct_orders"}


def test_require_ref_not_hardcoded(run):
    assert run("expect-no-hardcoded-refs") == {M + "fct_orders"}


def test_max_ctes(run):
    got = run("expect-max-ctes", include=["models/staging/**"], config={"max": 1})
    assert got == {M + "stg_customers"}


def test_require_import_cte_structure(run):
    assert M + "fct_orders" in run("expect-import-cte-structure")


# Fixtures with comments: stg_orders (line "-- TODO: ..."), dim_customers (block "/* ... */").


def test_comments_not_allowed(run):
    assert run("expect-comments", config={"allowed": False}) == {
        M + "stg_orders",
        M + "dim_customers",
    }


def test_comments_forbid_substring(run):
    assert run("expect-comments", config={"forbid": ["TODO"]}) == {M + "stg_orders"}


def test_comments_no_block(run):
    assert run("expect-comments", config={"allow_block": False}) == {M + "dim_customers"}


def test_comments_max_length(run):
    assert run("expect-comments", config={"max_length": 5}) == {
        M + "stg_orders",
        M + "dim_customers",
    }


def test_comments_allowed_by_default_no_violations(run):
    assert run("expect-comments") == set()
