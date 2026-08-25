from __future__ import annotations

M = "model.demo."
MARTS = ["models/marts/**"]


def test_min_tests_per_model(run):
    got = run("expect-min-tests-per-model", include=MARTS, config={"min": 1})
    assert got == {M + "fct_orders", M + "orders_summary"}


def test_min_tests_per_model_presence(run):
    # min:1 == "has any test": stg_customers/dim_customers have tests, the rest don't.
    assert run("expect-min-tests-per-model", config={"min": 1}) == {
        M + "stg_orders",
        M + "fct_orders",
        M + "orders_summary",
        M + "rpt_revenue",
    }


def test_min_tests_per_source(run):
    # neither source has a data test in the fixture
    assert run("expect-min-tests-per-source", config={"min": 1}) == {
        "source.demo.raw.customers",
        "source.demo.raw.orders",
    }


def test_require_primary_key(run):
    got = run("expect-primary-key", include=MARTS)
    assert got == {M + "fct_orders", M + "orders_summary"}


def test_require_unit_tests(run):
    got = run("expect-unit-tests", include=MARTS)
    assert got == {M + "fct_orders", M + "orders_summary"}


def test_source_freshness(run):
    assert run("expect-source-freshness") == {"source.demo.raw.orders"}


def test_no_disabled_nodes(run):
    assert run("expect-no-disabled-nodes") == {"model.demo.deprecated_model"}


def test_require_contract(run):
    got = run("expect-contract", include=MARTS)
    assert got == {M + "fct_orders", M + "orders_summary"}
