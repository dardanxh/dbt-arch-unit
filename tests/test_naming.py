from __future__ import annotations

M = "model.demo."


def test_layer_name_prefix(run):
    assert run("expect-layer-name-prefix") == {M + "orders_summary"}


def test_staging_name_matches_source(run):
    got = run("expect-staging-name-matches-source", severity="warning")
    assert got == {M + "stg_customers", M + "stg_orders"}


def test_model_name_regex_forbid(run):
    assert run("expect-model-name-regex", config={"forbid": ["summary"]}) == {M + "orders_summary"}


# Fixture model names: stg_customers, stg_orders, dim_customers, fct_orders,
# orders_summary, rpt_revenue — all snake_case.
_ALL = {
    M + "stg_customers",
    M + "stg_orders",
    M + "dim_customers",
    M + "fct_orders",
    M + "orders_summary",
    M + "rpt_revenue",
}


def test_name_convention_snake_ok(run):
    assert run("expect-model-name-convention", config={"case": "snake_case"}) == set()


def test_name_convention_camel_flags_all(run):
    # "underscore"/kabob/camel aliases accepted; all fixture names are snake, not camel
    assert run("expect-model-name-convention", config={"case": "camel"}) == _ALL


def test_name_convention_prefix(run):
    got = run("expect-model-name-convention", config={"prefix": "stg_"})
    assert got == {M + "dim_customers", M + "fct_orders", M + "orders_summary", M + "rpt_revenue"}


def test_name_convention_suffix(run):
    got = run("expect-model-name-convention", config={"suffix": "_orders"})
    assert got == {
        M + "stg_customers",
        M + "dim_customers",
        M + "orders_summary",
        M + "rpt_revenue",
    }


def test_name_convention_max_length(run):
    got = run("expect-model-name-convention", config={"max_length": 10})
    assert got == {
        M + "stg_customers",
        M + "dim_customers",
        M + "orders_summary",
        M + "rpt_revenue",
    }
